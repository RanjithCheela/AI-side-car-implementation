package com.bfsi.loan.consumer;

import com.bfsi.loan.model.LoanApplicationEvent;
import com.bfsi.loan.service.LoanProcessingService;
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
public class LoanApplicationConsumer {

    private final LoanProcessingService loanProcessingService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @KafkaListener(
        topics = "${kafka.topics.loan-allowed:loan-allowed}",
        groupId = "loan-origination-group",
        containerFactory = "kafkaListenerContainerFactory"
    )
    public void consumeApprovedApplication(ConsumerRecord<String, String> record, Acknowledgment ack) {
        String applicationId = record.key();
        log.info("[{}] Received approved loan application from Kafka (offset={})",
                applicationId, record.offset());

        try {
            LoanApplicationEvent event = objectMapper.readValue(record.value(), LoanApplicationEvent.class);
            loanProcessingService.processApprovedApplication(event);
            ack.acknowledge();
            log.info("[{}] Successfully processed and acknowledged", applicationId);
        } catch (Exception e) {
            log.error("[{}] Failed to process loan application: {}", applicationId, e.getMessage(), e);
            // In production: send to dead-letter topic
            ack.acknowledge();
        }
    }
}
