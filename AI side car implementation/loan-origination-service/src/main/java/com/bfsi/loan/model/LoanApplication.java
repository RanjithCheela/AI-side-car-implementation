package com.bfsi.loan.model;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "loan_applications")
@Data
@NoArgsConstructor
public class LoanApplication {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private String id;

    @Column(unique = true, nullable = false)
    private String applicationId;

    private String customerId;
    private String customerName;
    private String customerEmail;
    private String customerPhone;

    private BigDecimal loanAmount;
    private String loanPurpose;
    private Integer tenureMonths;
    private BigDecimal monthlyIncome;
    private String employmentType;

    private String status;           // PROCESSING / APPROVED / REJECTED / DISBURSED
    private BigDecimal interestRate;
    private BigDecimal emi;

    private double riskScore;
    private String riskLevel;
    private String intent;
    private String policyRule;

    private LocalDateTime receivedAt;
    private LocalDateTime processedAt;
    private String processingNotes;
}
