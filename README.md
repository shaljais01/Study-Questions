# Study-Questions

#1

Problem Statement
Design a Meeting Scheduler System that supports scheduling meetings across N rooms, while maintaining audit logs, respecting room capacities, and minimizing spillage of free time.

Error

🎯 Functional Requirements

1. Room Management

There are N rooms, each with a unique ID and a capacity.
2. Schedule Meeting

Method: schedule(meetingId, startTime, endTime, requiredCapacity)
Schedule a meeting in one of the available rooms that:
Is available during the given time slot.
Has sufficient capacity.
Minimizes spillage (i.e., try to avoid blocking longer available slots with short meetings).
If no room can host the meeting, return failure.
3. Audit Logs

Testing

Maintain an audit log for each scheduled meeting per room.
Each log includes:
meetingId
startTime, endTime
scheduledAt timestamp
Logs are stored per room.
4. Delete Expired Logs

Method: deleteExpiredLogs(xDays)
Delete audit logs older than x days (from scheduledAt time).


🔄 Non-Functional & Concurrency Requirements

System must be thread-safe:
Multiple scheduling and deletion requests may happen concurrently.
Use locking or concurrent data structures to avoid race conditions.
Optimize for read-heavy, low-latency scheduling.
➕ Follow-up Feature: Capacity Constraints

Each meeting has a requiredCapacity.
Rooms must be filtered by whether they can handle that many attendees.
🧠 Spillage Minimization (Key Constraint)

A short meeting should not be scheduled in a room that has a longer continuous block available unless no better-fit room is found.
				📌 Example:


text
CopyEdit
Room 1: Free from 9–10
Room 2: Free from 9–12
Meeting: 9–10, capacity 4

Prefer Room 1 → using Room 2 would waste 2 more hours of available time.

import java.time.Instant;
import java.util.*;
import java.util.concurrent.locks.*;

// ------------------- Meeting Class -------------------
class Meeting {
    String meetingId;
    long startTime;
    long endTime;
    int requiredCapacity;

    Meeting(String id, long start, long end, int capacity) {
        this.meetingId = id;
        this.startTime = start;
        this.endTime = end;
        this.requiredCapacity = capacity;
    }
}

// ------------------- Audit Log -------------------
class AuditLog {
    String meetingId;
    long startTime;
    long endTime;
    Instant scheduledAt;

    AuditLog(Meeting m) {
        this.meetingId = m.meetingId;
        this.startTime = m.startTime;
        this.endTime = m.endTime;
        this.scheduledAt = Instant.now();
    }
}

// ------------------- Gap Class -------------------
class Gap {
    long start, end;
    Gap(long s, long e) { start = s; end = e; }
    long length() { return end - start; }
}

// ------------------- Room -------------------
class Room {
    String roomId;
    int capacity;

    PriorityQueue<Gap> freeGaps;
    List<Meeting> meetings = new ArrayList<>();
    Queue<AuditLog> auditLogs = new LinkedList<>();

    private final ReentrantLock lock = new ReentrantLock();

    Room(String id, int cap, long dayStart, long dayEnd) {
        this.roomId = id;
        this.capacity = cap;
        // PQ sorted by gap length ascending → best-fit allocation
        freeGaps = new PriorityQueue<>(Comparator.comparingLong(Gap::length));
        freeGaps.add(new Gap(dayStart, dayEnd)); // initially whole day is free
    }

    boolean schedule(Meeting m) {
        lock.lock();
        try {
            if (m.requiredCapacity > capacity) return false;

            Gap bestGap = null;
            for (Gap g : freeGaps) {
                if (g.length() >= (m.endTime - m.startTime)) {
                    bestGap = g;
                    break;
                }
            }

            if (bestGap == null) return false;

            freeGaps.remove(bestGap);

            // Split gap into left and right portions if any
            if (bestGap.start < m.startTime)
                freeGaps.add(new Gap(bestGap.start, m.startTime));
            if (m.endTime < bestGap.end)
                freeGaps.add(new Gap(m.endTime, bestGap.end));

            meetings.add(m);
            auditLogs.add(new AuditLog(m));
            return true;
        } finally {
            lock.unlock();
        }
    }

    void deleteExpiredLogs(int xDays) {
        lock.lock();
        try {
            Instant threshold = Instant.now().minusSeconds(xDays * 24L * 3600);
            while (!auditLogs.isEmpty() && auditLogs.peek().scheduledAt.isBefore(threshold)) {
                auditLogs.poll();
            }
        } finally {
            lock.unlock();
        }
    }
}

// ------------------- Scheduler -------------------
class MeetingScheduler {
    List<Room> rooms;

    MeetingScheduler(List<Room> rms) {
        this.rooms = rms;
    }

    String schedule(String meetingId, long start, long end, int requiredCapacity) {
        Meeting m = new Meeting(meetingId, start, end, requiredCapacity);
        Room bestRoom = null;
        long minSpillage = Long.MAX_VALUE;

        for (Room r : rooms) {
            r.lock.lock();
            try {
                if (r.capacity < requiredCapacity) continue;

                // Best-fit from room's PQ
                Gap bestGap = null;
                for (Gap g : r.freeGaps) {
                    if (g.length() >= (m.endTime - m.startTime)) {
                        bestGap = g;
                        break;
                    }
                }

                if (bestGap != null) {
                    long spillage = bestGap.length() - (m.endTime - m.startTime);
                    if (spillage < minSpillage) {
                        minSpillage = spillage;
                        bestRoom = r;
                    }
                }
            } finally {
                r.lock.unlock();
            }
        }

        if (bestRoom != null && bestRoom.schedule(m)) {
            return "Meeting scheduled in Room " + bestRoom.roomId + " with spillage " + minSpillage;
        }
        return "No room available";
    }

    void deleteExpiredLogs(int xDays) {
        for (Room r : rooms) {
            r.deleteExpiredLogs(xDays);
        }
    }
}

// ------------------- Example Usage -------------------
public class Main {
    public static void main(String[] args) {
        Room r1 = new Room("R1", 10, 9*60, 17*60); // 9AM-5PM in minutes
        Room r2 = new Room("R2", 5, 9*60, 17*60);
        List<Room> rooms = Arrays.asList(r1, r2);
        MeetingScheduler scheduler = new MeetingScheduler(rooms);

        System.out.println(scheduler.schedule("M1", 540, 600, 4)); // 9-10AM
        System.out.println(scheduler.schedule("M2", 555, 585, 3)); // 9:15-9:45AM
        System.out.println(scheduler.schedule("M3", 600, 630, 2)); // 10-10:30AM
    }
}
