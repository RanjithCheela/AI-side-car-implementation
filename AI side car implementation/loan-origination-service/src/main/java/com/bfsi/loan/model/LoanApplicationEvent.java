package com.bfsi.loan.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class LoanApplicationEvent {

    private String eventType;
    private String applicationId;
    private String action;
    private double riskScore;
    private String riskLevel;
    private String intent;
    private double confidence;
    private List<String> fraudIndicators;
    private String policyRule;
    private String reason;
    private String timestamp;

    private Map<String, Object> loanDetails;
    private Map<String, Object> applicantDetails;
}
