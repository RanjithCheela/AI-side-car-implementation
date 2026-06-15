package com.bfsi.notification.consumer;

import com.bfsi.notification.model.DecisionEvent;
import com.bfsi.notification.service.EmailNotificationService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class DecisionEventConsumer {

    private final EmailNotificationService emailService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @KafkaListener(
        topics = "${kafka.topics.loan-notifications:loan-notifications}",
        groupId = "notification-service-group",
        containerFactory = "kafkaListenerContainerFactory"
    )
    public void consumeDecisionEvent(ConsumerRecord<String, String> record, Acknowledgment ack) {
        String applicationId = record.key();
        log.info("[{}] Received decision event (offset={})", applicationId, record.offset());

        try {
            DecisionEvent event = objectMapper.readValue(record.value(), DecisionEvent.class);
            emailService.sendDecisionNotifications(event);
            ack.acknowledge();
        } catch (Exception e) {
            log.error("[{}] Failed to process notification event: {}", applicationId, e.getMessage(), e);
            ack.acknowledge(); // Acknowledge to avoid infinite retry — DLQ in production
        }
    }
}
