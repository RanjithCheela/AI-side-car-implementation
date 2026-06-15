import redis.asyncio as aioredis
import hashlib
import json
from shared.models import LoanApplicationRequest, ContextObject, BehaviorHistory, DeviceGeoInfo, KYCAMLStatus
from config import settings
import logging

logger = logging.getLogger(__name__)


class ContextEnrichmentService:
    """
    Enriches loan applications with behavioral, geo, and KYC/AML context.
    In production, external API calls (IP intelligence, KYC bureau, AML watchlists)
    replace the hash-based simulations used here for MVP.
    """

    def __init__(self):
        self.redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    async def enrich(self, application: LoanApplicationRequest) -> ContextObject:
        customer_id = application.applicant.customer_id
        device_id = application.device.device_id
        ip = application.device.ip_address

        behavior = await self._get_behavior_history(customer_id)
        device_geo = await self._get_device_geo_info(ip, device_id)
        kyc_aml = await self._get_kyc_aml_status(customer_id, application.applicant.national_id)

        await self._record_attempt(customer_id, device_id, ip, application.application_id)

        return ContextObject(
            application_id=application.application_id,
            behavior=behavior,
            device_geo=device_geo,
            kyc_aml=kyc_aml,
        )

    async def _get_behavior_history(self, customer_id: str) -> BehaviorHistory:
        try:
            apps_24h = await self.redis.scard(f"apps:24h:{customer_id}") or 0
            apps_7d = await self.redis.scard(f"apps:7d:{customer_id}") or 0
            apps_30d = await self.redis.scard(f"apps:30d:{customer_id}") or 0
            fraud_flags = int(await self.redis.get(f"fraud_flags:{customer_id}") or 0)
            devices_used = await self.redis.scard(f"devices:{customer_id}") or 1
            ip_changes = await self.redis.scard(f"ips:7d:{customer_id}") or 0

            h = int(hashlib.md5(customer_id.encode()).hexdigest(), 16)
            previous_defaults = h % 3

            return BehaviorHistory(
                applications_last_24h=apps_24h,
                applications_last_7d=apps_7d,
                applications_last_30d=apps_30d,
                previous_defaults=previous_defaults,
                previous_fraud_flags=fraud_flags,
                devices_used=max(1, devices_used),
                ip_changes_last_7d=ip_changes,
            )
        except Exception as e:
            logger.warning(f"Redis behavior lookup failed: {e}")
            return BehaviorHistory()

    async def _get_device_geo_info(self, ip: str, device_id: str) -> DeviceGeoInfo:
        try:
            cached = await self.redis.get(f"ip_info:{ip}")
            if cached:
                return DeviceGeoInfo(**json.loads(cached))

            h = int(hashlib.md5(ip.encode()).hexdigest(), 16)
            ip_risk = float(h % 35)
            is_vpn = ip.startswith(("10.", "172.16.", "192.168."))
            is_proxy = (h % 25 == 0)

            device_seen = bool(await self.redis.exists(f"device:{device_id}"))

            info = DeviceGeoInfo(
                ip_country="IN",
                ip_city="Mumbai",
                ip_is_vpn=is_vpn,
                ip_is_proxy=is_proxy,
                ip_risk_score=ip_risk,
                device_seen_before=device_seen,
                location_matches_profile=not (is_vpn or is_proxy),
            )
            await self.redis.setex(f"ip_info:{ip}", 3600, json.dumps(info.model_dump()))
            return info
        except Exception as e:
            logger.warning(f"Device/geo lookup failed: {e}")
            return DeviceGeoInfo()

    async def _get_kyc_aml_status(self, customer_id: str, national_id: str) -> KYCAMLStatus:
        try:
            cached = await self.redis.get(f"kyc:{customer_id}")
            if cached:
                return KYCAMLStatus(**json.loads(cached))

            h = int(hashlib.md5(national_id.encode()).hexdigest(), 16)
            on_sanctions = (h % 100 == 0)   # 1% hit rate
            aml_flagged = (h % 30 == 0)      # ~3%
            kyc_ok = (h % 25 != 1)           # ~96% verified

            status = KYCAMLStatus(
                kyc_verified=kyc_ok,
                aml_status="flagged" if aml_flagged else "clear",
                sanctions_list=on_sanctions,
                pep_status=False,
                adverse_media=aml_flagged,
            )
            await self.redis.setex(f"kyc:{customer_id}", 86400, json.dumps(status.model_dump()))
            return status
        except Exception as e:
            logger.warning(f"KYC/AML lookup failed: {e}")
            return KYCAMLStatus()

    async def _record_attempt(self, customer_id: str, device_id: str, ip: str, app_id: str):
        try:
            pipe = self.redis.pipeline()
            pipe.sadd(f"apps:24h:{customer_id}", app_id); pipe.expire(f"apps:24h:{customer_id}", 86400)
            pipe.sadd(f"apps:7d:{customer_id}", app_id);  pipe.expire(f"apps:7d:{customer_id}", 604800)
            pipe.sadd(f"apps:30d:{customer_id}", app_id); pipe.expire(f"apps:30d:{customer_id}", 2592000)
            pipe.sadd(f"devices:{customer_id}", device_id); pipe.expire(f"devices:{customer_id}", 2592000)
            pipe.sadd(f"ips:7d:{customer_id}", ip);       pipe.expire(f"ips:7d:{customer_id}", 604800)
            pipe.setex(f"device:{device_id}", 2592000, customer_id)
            await pipe.execute()
        except Exception as e:
            logger.warning(f"Failed to record application attempt in Redis: {e}")

    async def flag_fraud(self, customer_id: str):
        try:
            await self.redis.incr(f"fraud_flags:{customer_id}")
            await self.redis.expire(f"fraud_flags:{customer_id}", 7776000)  # 90 days
        except Exception as e:
            logger.warning(f"Failed to flag fraud for {customer_id}: {e}")

    async def close(self):
        await self.redis.aclose()
