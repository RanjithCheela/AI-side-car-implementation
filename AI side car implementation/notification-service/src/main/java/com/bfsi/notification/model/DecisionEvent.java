package com.bfsi.notification.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class DecisionEvent {

    @JsonProperty("event_type")
    private String eventType;

    @JsonProperty("application_id")
    private String applicationId;

    @JsonProperty("action")
    private String action;

    @JsonProperty("risk_score")
    private double riskScore;

    @JsonProperty("risk_level")
    private String riskLevel;

    @JsonProperty("intent")
    private String intent;

    @JsonProperty("confidence")
    private double confidence;

    @JsonProperty("fraud_indicators")
    private List<String> fraudIndicators;

    @JsonProperty("policy_rule")
    private String policyRule;

    @JsonProperty("reason")
    private String reason;

    @JsonProperty("requires_manual_review")
    private boolean requiresManualReview;

    @JsonProperty("requires_verification")
    private boolean requiresVerification;

    @JsonProperty("verification_type")
    private String verificationType;

    @JsonProperty("applicant_name")
    private String applicantName;

    @JsonProperty("applicant_email")
    private String applicantEmail;

    @JsonProperty("applicant_customer_id")
    private String applicantCustomerId;

    @JsonProperty("loan_amount")
    private double loanAmount;

    @JsonProperty("loan_purpose")
    private String loanPurpose;

    @JsonProperty("next_steps")
    private List<String> nextSteps;

    @JsonProperty("message")
    private String message;

    @JsonProperty("stakeholder_emails")
    private List<String> stakeholderEmails;

    @JsonProperty("timestamp")
    private String timestamp;
}
