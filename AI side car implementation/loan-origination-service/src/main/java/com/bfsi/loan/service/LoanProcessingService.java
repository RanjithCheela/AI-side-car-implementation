package com.bfsi.loan.service;

import com.bfsi.loan.model.LoanApplication;
import com.bfsi.loan.model.LoanApplicationEvent;
import com.bfsi.loan.repository.LoanApplicationRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class LoanProcessingService {

    private final LoanApplicationRepository repository;

    public void processApprovedApplication(LoanApplicationEvent event) {
        String appId = event.getApplicationId();

        if (repository.existsByApplicationId(appId)) {
            log.warn("[{}] Duplicate application received — skipping", appId);
            return;
        }

        LoanApplication loan = buildLoanApplication(event);
        enrichWithFinancials(loan);
        loan.setStatus("PROCESSING");
        loan.setProcessedAt(LocalDateTime.now());

        repository.save(loan);

        log.info("[{}] Loan application saved — customer={}, amount=₹{}, EMI=₹{}, rate={}%",
                appId, loan.getCustomerName(), loan.getLoanAmount(), loan.getEmi(), loan.getInterestRate());

        simulateCreditDecision(loan);
    }

    private LoanApplication buildLoanApplication(LoanApplicationEvent event) {
        Map<String, Object> ld = event.getLoanDetails();
        Map<String, Object> ad = event.getApplicantDetails();

        LoanApplication loan = new LoanApplication();
        loan.setApplicationId(event.getApplicationId());
        loan.setRiskScore(event.getRiskScore());
        loan.setRiskLevel(event.getRiskLevel());
        loan.setIntent(event.getIntent());
        loan.setPolicyRule(event.getPolicyRule());
        loan.setReceivedAt(LocalDateTime.now());

        if (ld != null) {
            loan.setLoanAmount(toBigDecimal(ld.get("amount")));
            loan.setLoanPurpose((String) ld.get("purpose"));
            loan.setTenureMonths(toInt(ld.get("tenure_months")));
            loan.setMonthlyIncome(toBigDecimal(ld.get("monthly_income")));
            loan.setEmploymentType((String) ld.get("employment_type"));
        }

        if (ad != null) {
            loan.setCustomerId((String) ad.get("customer_id"));
            loan.setCustomerName((String) ad.get("name"));
            loan.setCustomerEmail((String) ad.get("email"));
            loan.setCustomerPhone((String) ad.get("phone"));
        }

        return loan;
    }

    private void enrichWithFinancials(LoanApplication loan) {
        double baseRate = 10.5;
        double riskPremium = loan.getRiskScore() * 0.05;  // 0-5% premium based on risk
        double finalRate = Math.min(baseRate + riskPremium, 24.0);
        loan.setInterestRate(BigDecimal.valueOf(finalRate).setScale(2, RoundingMode.HALF_UP));

        if (loan.getLoanAmount() != null && loan.getTenureMonths() != null) {
            double principal = loan.getLoanAmount().doubleValue();
            double monthlyRate = finalRate / 12 / 100;
            int n = loan.getTenureMonths();
            double emi = (principal * monthlyRate * Math.pow(1 + monthlyRate, n))
                    / (Math.pow(1 + monthlyRate, n) - 1);
            loan.setEmi(BigDecimal.valueOf(emi).setScale(2, RoundingMode.HALF_UP));
        }
    }

    private void simulateCreditDecision(LoanApplication loan) {
        // In production: call credit bureau, underwriting engine, etc.
        double dti = 0;
        if (loan.getMonthlyIncome() != null && loan.getEmi() != null) {
            dti = loan.getEmi().doubleValue() / loan.getMonthlyIncome().doubleValue();
        }

        String status;
        String notes;
        if (dti > 0.6) {
            status = "REJECTED";
            notes = String.format("DTI ratio %.1f%% exceeds 60%% threshold", dti * 100);
        } else if (loan.getRiskScore() > 30) {
            status = "APPROVED";
            notes = "Approved with standard documentation verification";
        } else {
            status = "APPROVED";
            notes = "Pre-approved — disbursement pending KYC confirmation";
        }

        loan.setStatus(status);
        loan.setProcessingNotes(notes);
        repository.save(loan);

        log.info("[{}] Credit decision: {} — {}", loan.getApplicationId(), status, notes);
    }

    private BigDecimal toBigDecimal(Object val) {
        if (val == null) return BigDecimal.ZERO;
        return new BigDecimal(val.toString());
    }

    private Integer toInt(Object val) {
        if (val == null) return 0;
        return ((Number) val).intValue();
    }
}
