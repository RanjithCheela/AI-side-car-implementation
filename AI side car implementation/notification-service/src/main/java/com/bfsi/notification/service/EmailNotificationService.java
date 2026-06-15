package com.bfsi.notification.service;

import com.bfsi.notification.model.DecisionEvent;
import jakarta.mail.internet.MimeMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;
import org.thymeleaf.TemplateEngine;
import org.thymeleaf.context.Context;

import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class EmailNotificationService {

    private final JavaMailSender mailSender;
    private final TemplateEngine templateEngine;

    @Value("${notification.from-email}")
    private String fromEmail;

    @Value("${notification.from-name}")
    private String fromName;

    @Value("${notification.fraud-team-emails}")
    private String fraudTeamEmails;

    @Value("${notification.loan-ops-emails}")
    private String loanOpsEmails;

    @Value("${notification.branch-manager-email}")
    private String branchManagerEmail;

    @Value("${notification.compliance-email}")
    private String complianceEmail;

    public void sendDecisionNotifications(DecisionEvent event) {
        String action = event.getAction();
        log.info("[{}] Sending notifications for action={}", event.getApplicationId(), action);

        switch (action) {
            case "BLOCK"     -> handleBlock(event);
            case "ESCALATE"  -> handleEscalate(event);
            case "CHALLENGE" -> handleChallenge(event);
            case "ALLOW"     -> handleAllow(event);
            default          -> log.warn("[{}] Unknown action: {}", event.getApplicationId(), action);
        }
    }

    private void handleBlock(DecisionEvent event) {
        // 1. Notify fraud operations team
        List<String> fraudTeam = splitEmails(fraudTeamEmails);
        sendEmail(fraudTeam, buildFraudTeamSubject(event), buildTemplate("email-block-internal", event));

        // 2. Notify applicant (no fraud details disclosed)
        sendApplicantEmail(event, "email-block-applicant",
                "Update on Your Loan Application — Ref: " + event.getApplicationId());
    }

    private void handleEscalate(DecisionEvent event) {
        // 1. Fraud analyst team
        List<String> fraudTeam = splitEmails(fraudTeamEmails);
        sendEmail(fraudTeam, "[ACTION REQUIRED] Loan Application Escalated — " + event.getApplicationId(),
                buildTemplate("email-escalate-internal", event));

        // 2. Branch manager
        sendEmail(List.of(branchManagerEmail), "Escalation Alert — " + event.getApplicantName(),
                buildTemplate("email-escalate-internal", event));

        // 3. Compliance team (if AML-related)
        if ("ESCALATE_AML_FLAGGED".equals(event.getPolicyRule())) {
            sendEmail(List.of(complianceEmail), "[COMPLIANCE] AML Flag — " + event.getApplicationId(),
                    buildTemplate("email-escalate-internal", event));
        }

        // 4. Notify applicant
        sendApplicantEmail(event, "email-escalate-applicant",
                "Your Loan Application is Under Review — Ref: " + event.getApplicationId());
    }

    private void handleChallenge(DecisionEvent event) {
        // Notify applicant with verification instructions
        sendApplicantEmail(event, "email-challenge-applicant",
                "Action Required: Verify Your Identity — Ref: " + event.getApplicationId());

        // Notify loan ops team
        List<String> loanOps = splitEmails(loanOpsEmails);
        sendEmail(loanOps, "Verification Pending — " + event.getApplicationId(),
                buildTemplate("email-challenge-internal", event));
    }

    private void handleAllow(DecisionEvent event) {
        // Notify applicant
        sendApplicantEmail(event, "email-allow-applicant",
                "Good News! Your Loan Application is Being Processed — Ref: " + event.getApplicationId());

        // For large loans (> 10L), also notify loan ops
        if (event.getLoanAmount() > 1_000_000) {
            List<String> loanOps = splitEmails(loanOpsEmails);
            sendEmail(loanOps, "High-Value Loan Approved — " + event.getApplicationId(),
                    buildTemplate("email-allow-internal", event));
        }
    }

    private void sendApplicantEmail(DecisionEvent event, String template, String subject) {
        if (event.getApplicantEmail() == null || event.getApplicantEmail().isBlank()) {
            log.warn("[{}] No applicant email — skipping applicant notification", event.getApplicationId());
            return;
        }
        sendEmail(List.of(event.getApplicantEmail()), subject, buildTemplate(template, event));
    }

    private String buildTemplate(String templateName, DecisionEvent event) {
        Context ctx = new Context();
        ctx.setVariable("event", event);
        ctx.setVariable("applicationId", event.getApplicationId());
        ctx.setVariable("applicantName", event.getApplicantName());
        ctx.setVariable("loanAmount", String.format("₹%.2f", event.getLoanAmount()));
        ctx.setVariable("riskScore", event.getRiskScore());
        ctx.setVariable("riskLevel", event.getRiskLevel());
        ctx.setVariable("intent", event.getIntent());
        ctx.setVariable("policyRule", event.getPolicyRule());
        ctx.setVariable("reason", event.getReason());
        ctx.setVariable("fraudIndicators", event.getFraudIndicators());
        ctx.setVariable("nextSteps", event.getNextSteps());
        ctx.setVariable("verificationType", event.getVerificationType());
        ctx.setVariable("timestamp", event.getTimestamp());
        return templateEngine.process(templateName, ctx);
    }

    private void sendEmail(List<String> to, String subject, String htmlBody) {
        if (to == null || to.isEmpty()) return;
        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            helper.setFrom(fromEmail, fromName);
            helper.setTo(to.toArray(new String[0]));
            helper.setSubject(subject);
            helper.setText(htmlBody, true);
            mailSender.send(message);
            log.info("Email sent to {} — subject: {}", to, subject);
        } catch (Exception e) {
            log.error("Failed to send email to {}: {}", to, e.getMessage());
        }
    }

    private String buildFraudTeamSubject(DecisionEvent event) {
        return String.format("[FRAUD BLOCKED] %s | Risk: %.0f | %s",
                event.getApplicationId(), event.getRiskScore(), event.getIntent());
    }

    private List<String> splitEmails(String csv) {
        List<String> result = new ArrayList<>();
        if (csv == null || csv.isBlank()) return result;
        for (String e : csv.split(",")) {
            String trimmed = e.trim();
            if (!trimmed.isEmpty()) result.add(trimmed);
        }
        return result;
    }
}
