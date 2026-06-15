from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-opus-4-8"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_decisions: str = "loan-decisions"
    kafka_topic_notifications: str = "loan-notifications"
    kafka_topic_allowed: str = "loan-allowed"
    kafka_topic_escalations: str = "loan-escalations"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://bfsi:bfsi_secret_2024@localhost:5432/intent_firewall"

    # Stakeholder Emails
    fraud_team_emails: str = "fraud@bank.com"
    loan_ops_emails: str = "loanops@bank.com"
    branch_manager_email: str = "manager@bank.com"
    compliance_email: str = "compliance@bank.com"

    # App
    app_debug: bool = False

    def get_fraud_team_emails(self) -> List[str]:
        return [e.strip() for e in self.fraud_team_emails.split(",")]

    def get_loan_ops_emails(self) -> List[str]:
        return [e.strip() for e in self.loan_ops_emails.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
