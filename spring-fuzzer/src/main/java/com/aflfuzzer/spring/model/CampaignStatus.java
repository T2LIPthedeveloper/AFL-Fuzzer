package com.aflfuzzer.spring.model;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

public class CampaignStatus {
    public enum State { PENDING, RUNNING, COMPLETED, FAILED }

    private String id;
    private State state = State.PENDING;
    private int plannedIterations;
    private int completedIterations;
    private int interestingCount;
    private int crashCount;
    private Instant startedAt;
    private Instant finishedAt;
    private String message;
    private List<String> notes = new ArrayList<>();

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public State getState() { return state; }
    public void setState(State state) { this.state = state; }
    public int getPlannedIterations() { return plannedIterations; }
    public void setPlannedIterations(int plannedIterations) { this.plannedIterations = plannedIterations; }
    public int getCompletedIterations() { return completedIterations; }
    public void setCompletedIterations(int completedIterations) { this.completedIterations = completedIterations; }
    public int getInterestingCount() { return interestingCount; }
    public void setInterestingCount(int interestingCount) { this.interestingCount = interestingCount; }
    public int getCrashCount() { return crashCount; }
    public void setCrashCount(int crashCount) { this.crashCount = crashCount; }
    public Instant getStartedAt() { return startedAt; }
    public void setStartedAt(Instant startedAt) { this.startedAt = startedAt; }
    public Instant getFinishedAt() { return finishedAt; }
    public void setFinishedAt(Instant finishedAt) { this.finishedAt = finishedAt; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public List<String> getNotes() { return notes; }
    public void setNotes(List<String> notes) { this.notes = notes; }
}
