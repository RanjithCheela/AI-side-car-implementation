package com.bfsi.loan.repository;

import com.bfsi.loan.model.LoanApplication;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface LoanApplicationRepository extends JpaRepository<LoanApplication, String> {
    Optional<LoanApplication> findByApplicationId(String applicationId);
    boolean existsByApplicationId(String applicationId);
}
