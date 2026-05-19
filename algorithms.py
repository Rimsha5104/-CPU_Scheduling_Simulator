"""CPU scheduling algorithms and process models for the simulator.

This module keeps the scheduling logic separate from the graphical interface,
which makes the project easier to inspect, test, and package as an executable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Scheduling options shown in the UI and understood by the engine.
ALGORITHMS = [
    "FCFS",
    "SJF Non-Preemptive",
    "SRTF",
    "Priority Non-Preemptive",
    "Priority Preemptive",
    "Round Robin",
    "MLFQ",
]

# Reused process colors keep each process visually consistent in charts.
PALETTE = [
    "#00D4FF", "#7C5CFF", "#2EE59D", "#FFB703", "#FB5607",
    "#FF4D8D", "#38BDF8", "#A3E635", "#F97316", "#C084FC",
    "#14B8A6", "#F43F5E", "#EAB308", "#60A5FA", "#34D399",
]


@dataclass
class Process:
    pid: str
    arrival_time: int
    burst_time: int
    priority: int
    color: str
    remaining_time: int = field(init=False)
    executed_time: int = 0
    start_time: int | None = None
    completion_time: int | None = None
    response_time: int | None = None
    state: str = "NEW"
    queue_level: int = 0
    last_ready_time: int = 0
    quantum_used: int = 0
    waiting_score: int = 0

    def __post_init__(self):
        # Remaining time starts as the full burst and decreases on every CPU tick.
        self.remaining_time = max(0, int(self.burst_time))

    @property
    def is_completed(self) -> bool:
        return self.remaining_time <= 0

    @property
    def turnaround_time(self) -> int:
        if self.completion_time is None:
            return 0
        return max(0, self.completion_time - self.arrival_time)

    @property
    def waiting_time(self) -> int:
        if self.completion_time is not None:
            return max(0, self.turnaround_time - self.burst_time)
        return max(0, self.executed_live_time_reference - self.arrival_time - self.executed_time)

    @property
    def executed_live_time_reference(self) -> int:
        return getattr(self, "_clock", self.arrival_time)

    def set_clock(self, clock: int):
        self._clock = clock


class SchedulerEngine:
    """Discrete-time scheduler supporting all required algorithms."""

    def __init__(self, log_callback=None):
        self.log_callback = log_callback or (lambda text: None)
        self.processes: list[Process] = []
        self.current_time = 0
        self.busy_time = 0
        self.algorithm = ALGORITHMS[0]
        self.running_pid: str | None = None
        self.gantt: list[dict] = []
        self.completed_order: list[str] = []
        self.rr_queue: list[str] = []
        self.mlfq_queues: list[list[str]] = [[] for _ in range(3)]
        self.rr_quantum = 3
        self.mlfq_levels = 3
        self.mlfq_quantums = [2, 4, 8, 12, 16]
        self.aging_threshold = 8
        self.priority_boost_interval = 24
        self._color_index = 0

    def log(self, text: str):
        self.log_callback(f"[t={self.current_time:03d}] {text}")

    def add_process(self, pid: str, arrival: int, burst: int, priority: int):
        pid = pid.strip() or f"P{len(self.processes) + 1}"
        if any(p.pid == pid for p in self.processes):
            raise ValueError("Process ID already exists.")
        if arrival < 0 or burst <= 0 or priority < 0:
            raise ValueError("Arrival must be >= 0, burst > 0, and priority >= 0.")
        color = PALETTE[self._color_index % len(PALETTE)]
        self._color_index += 1
        process = Process(pid, int(arrival), int(burst), int(priority), color)
        process.last_ready_time = process.arrival_time
        self.processes.append(process)
        self.processes.sort(key=lambda p: (p.arrival_time, p.pid))
        self.log(f"Added {pid} (arrival={arrival}, burst={burst}, priority={priority}).")
        self.rebuild_queues()

    def edit_process(self, pid: str, new_pid: str, arrival: int, burst: int, priority: int):
        process = self.get_process(pid)
        if process is None:
            raise ValueError("Select a valid process to edit.")
        new_pid = new_pid.strip() or pid
        if new_pid != pid and any(p.pid == new_pid for p in self.processes):
            raise ValueError("New Process ID already exists.")
        if arrival < 0 or burst <= 0 or priority < 0:
            raise ValueError("Arrival must be >= 0, burst > 0, and priority >= 0.")
        old_burst = process.burst_time
        if new_pid != pid:
            for index, queued_pid in enumerate(self.rr_queue):
                if queued_pid == pid:
                    self.rr_queue[index] = new_pid
            for queue in self.mlfq_queues:
                for index, queued_pid in enumerate(queue):
                    if queued_pid == pid:
                        queue[index] = new_pid
            if self.running_pid == pid:
                self.running_pid = new_pid
            self.completed_order = [new_pid if item == pid else item for item in self.completed_order]
            process.pid = new_pid
        process.arrival_time = int(arrival)
        process.priority = int(priority)
        process.burst_time = int(burst)
        process.remaining_time = max(0, process.remaining_time + (process.burst_time - old_burst))
        if process.remaining_time <= 0 and process.completion_time is None:
            process.completion_time = self.current_time
            process.state = "DONE"
            if process.pid not in self.completed_order:
                self.completed_order.append(process.pid)
            if self.running_pid == process.pid:
                self.running_pid = None
        if process.completion_time is not None and process.remaining_time > 0:
            process.completion_time = None
            if process.pid in self.completed_order:
                self.completed_order.remove(process.pid)
        process.state = "READY" if process.arrival_time <= self.current_time and not process.is_completed else process.state
        self.log(f"Edited {new_pid} live.")
        self.rebuild_queues()

    def remove_process(self, pid: str):
        process = self.get_process(pid)
        if process is None:
            return
        self.processes = [p for p in self.processes if p.pid != pid]
        self.rr_queue = [item for item in self.rr_queue if item != pid]
        for queue in self.mlfq_queues:
            while pid in queue:
                queue.remove(pid)
        if self.running_pid == pid:
            self.running_pid = None
        if pid in self.completed_order:
            self.completed_order.remove(pid)
        self.log(f"Removed {pid}.")

    def reset(self):
        for process in self.processes:
            process.remaining_time = process.burst_time
            process.executed_time = 0
            process.start_time = None
            process.completion_time = None
            process.response_time = None
            process.state = "NEW"
            process.queue_level = 0
            process.quantum_used = 0
            process.waiting_score = 0
            process.last_ready_time = process.arrival_time
        self.current_time = 0
        self.busy_time = 0
        self.running_pid = None
        self.gantt.clear()
        self.completed_order.clear()
        self.rebuild_queues()
        self.log("Simulation reset.")

    def set_algorithm(self, algorithm: str):
        if algorithm not in ALGORITHMS:
            return
        self.algorithm = algorithm
        self.running_pid = None if "Preemptive" in algorithm or algorithm in {"SRTF", "Round Robin", "MLFQ"} else self.running_pid
        self.rebuild_queues()
        self.log(f"Switched algorithm to {algorithm}.")

    def get_process(self, pid: str | None) -> Process | None:
        if pid is None:
            return None
        for process in self.processes:
            if process.pid == pid:
                return process
        return None

    def arrived_unfinished(self) -> list[Process]:
        return [p for p in self.processes if p.arrival_time <= self.current_time and not p.is_completed]

    def ready_processes(self) -> list[Process]:
        return [p for p in self.arrived_unfinished() if p.pid != self.running_pid]

    def rebuild_queues(self):
        active = [p.pid for p in self.arrived_unfinished()]
        self.rr_queue = [pid for pid in self.rr_queue if pid in active and pid != self.running_pid]
        for process in self.arrived_unfinished():
            if process.pid != self.running_pid and process.pid not in self.rr_queue:
                self.rr_queue.append(process.pid)
        self.mlfq_queues = [[] for _ in range(max(1, self.mlfq_levels))]
        for process in self.arrived_unfinished():
            level = min(process.queue_level, self.mlfq_levels - 1)
            if process.pid != self.running_pid:
                self.mlfq_queues[level].append(process.pid)

    def tick(self):
        # Advance the simulation by exactly one time unit.
        for process in self.processes:
            process.set_clock(self.current_time)
            if process.is_completed:
                process.state = "DONE"
            elif process.arrival_time > self.current_time:
                process.state = "NEW"
            elif process.pid != self.running_pid:
                process.state = "READY"

        if self.algorithm == "Round Robin":
            selected = self._select_round_robin()
        elif self.algorithm == "MLFQ":
            selected = self._select_mlfq()
        else:
            selected = self._select_standard()

        if selected is None:
            self._record_gantt("IDLE", "#64748B")
            self.running_pid = None
            self.current_time += 1
            return

        if self.running_pid != selected.pid:
            selected.quantum_used = 0
            self.running_pid = selected.pid
            self.log(f"CPU dispatched {selected.pid}.")

        self._execute_one_unit(selected)
        self.current_time += 1

        if selected.remaining_time <= 0:
            selected.state = "DONE"
            selected.completion_time = self.current_time
            self.completed_order.append(selected.pid)
            self.log(f"{selected.pid} completed.")
            self.running_pid = None
            self._remove_from_all_queues(selected.pid)

    def _execute_one_unit(self, process: Process):
        if process.start_time is None:
            process.start_time = self.current_time
            process.response_time = max(0, self.current_time - process.arrival_time)
        process.state = "RUNNING"
        process.remaining_time -= 1
        process.executed_time += 1
        process.quantum_used += 1
        self.busy_time += 1
        self._record_gantt(process.pid, process.color)

    def _record_gantt(self, pid: str, color: str):
        if self.gantt and self.gantt[-1]["pid"] == pid and self.gantt[-1]["end"] == self.current_time:
            self.gantt[-1]["end"] = self.current_time + 1
        else:
            self.gantt.append({
                "start": self.current_time,
                "end": self.current_time + 1,
                "pid": pid,
                "color": color,
                "algorithm": self.algorithm,
            })

    def _select_standard(self) -> Process | None:
        running = self.get_process(self.running_pid)
        non_preemptive = self.algorithm in {"FCFS", "SJF Non-Preemptive", "Priority Non-Preemptive"}
        if running and not running.is_completed and non_preemptive:
            return running

        ready = self.arrived_unfinished()
        if not ready:
            return None
        if self.algorithm == "FCFS":
            return sorted(ready, key=lambda p: (p.arrival_time, p.pid))[0]
        if self.algorithm == "SJF Non-Preemptive":
            return sorted(ready, key=lambda p: (p.burst_time, p.arrival_time, p.pid))[0]
        if self.algorithm == "SRTF":
            return sorted(ready, key=lambda p: (p.remaining_time, p.arrival_time, p.pid))[0]
        if self.algorithm == "Priority Non-Preemptive":
            return sorted(ready, key=lambda p: (p.priority, p.arrival_time, p.pid))[0]
        if self.algorithm == "Priority Preemptive":
            return sorted(ready, key=lambda p: (p.priority, p.arrival_time, p.pid))[0]
        return ready[0]

    def _select_round_robin(self) -> Process | None:
        active = [p.pid for p in self.arrived_unfinished()]
        self.rr_queue = [pid for pid in self.rr_queue if pid in active]
        for process in self.arrived_unfinished():
            if process.pid != self.running_pid and process.pid not in self.rr_queue:
                self.rr_queue.append(process.pid)

        running = self.get_process(self.running_pid)
        if running and not running.is_completed and running.quantum_used < max(1, self.rr_quantum):
            return running
        if running and not running.is_completed and running.quantum_used >= max(1, self.rr_quantum):
            running.quantum_used = 0
            self.rr_queue.append(running.pid)
            self.log(f"Quantum expired for {running.pid}.")
            self.running_pid = None

        while self.rr_queue:
            candidate = self.get_process(self.rr_queue.pop(0))
            if candidate and not candidate.is_completed and candidate.arrival_time <= self.current_time:
                return candidate
        return None

    def _select_mlfq(self) -> Process | None:
        if self.current_time > 0 and self.priority_boost_interval > 0:
            if self.current_time % self.priority_boost_interval == 0:
                for process in self.arrived_unfinished():
                    if process.pid != self.running_pid:
                        process.queue_level = 0
                self.log("MLFQ priority boost moved waiting jobs to queue 0.")

        for process in self.ready_processes():
            waited = self.current_time - process.last_ready_time
            if waited >= max(2, self.aging_threshold) and process.queue_level > 0:
                process.queue_level -= 1
                process.last_ready_time = self.current_time
                self.log(f"Aging promoted {process.pid} to Q{process.queue_level}.")

        self.rebuild_queues()
        running = self.get_process(self.running_pid)
        if running and not running.is_completed:
            higher_ready = any(self.mlfq_queues[level] for level in range(running.queue_level))
            quantum = self.mlfq_quantums[min(running.queue_level, len(self.mlfq_quantums) - 1)]
            if not higher_ready and running.quantum_used < quantum:
                return running
            if running.quantum_used >= quantum:
                running.queue_level = min(self.mlfq_levels - 1, running.queue_level + 1)
                running.quantum_used = 0
                running.last_ready_time = self.current_time
                self.running_pid = None
                self.log(f"{running.pid} moved to MLFQ Q{running.queue_level}.")

        self.rebuild_queues()
        for level, queue in enumerate(self.mlfq_queues):
            while queue:
                candidate = self.get_process(queue.pop(0))
                if candidate and not candidate.is_completed and candidate.arrival_time <= self.current_time:
                    candidate.queue_level = level
                    return candidate
        return None

    def _remove_from_all_queues(self, pid: str):
        self.rr_queue = [item for item in self.rr_queue if item != pid]
        for queue in self.mlfq_queues:
            while pid in queue:
                queue.remove(pid)

    def metrics(self) -> dict:
        # Calculate live performance values used by the dashboard and reports.
        for process in self.processes:
            process.set_clock(self.current_time)
        completed = [p for p in self.processes if p.is_completed and p.completion_time is not None]
        arrived = [p for p in self.processes if p.arrival_time <= self.current_time]
        waiting_values = [self.live_waiting_time(p) for p in arrived]
        turnaround_values = [self.live_turnaround_time(p) for p in arrived]
        response_values = [p.response_time for p in self.processes if p.response_time is not None]
        total_time = max(1, self.current_time)
        return {
            "avg_waiting": sum(waiting_values) / len(waiting_values) if waiting_values else 0,
            "avg_turnaround": sum(turnaround_values) / len(turnaround_values) if turnaround_values else 0,
            "cpu_utilization": (self.busy_time / total_time) * 100,
            "throughput": len(completed) / total_time,
            "avg_response": sum(response_values) / len(response_values) if response_values else 0,
            "completed": len(completed),
            "total": len(self.processes),
            "completion_order": " > ".join(self.completed_order) if self.completed_order else "None yet",
        }

    def live_waiting_time(self, process: Process) -> int:
        if process.completion_time is not None:
            return max(0, process.completion_time - process.arrival_time - process.burst_time)
        if process.arrival_time > self.current_time:
            return 0
        return max(0, self.current_time - process.arrival_time - process.executed_time)

    def live_turnaround_time(self, process: Process) -> int:
        if process.completion_time is not None:
            return max(0, process.completion_time - process.arrival_time)
        if process.arrival_time > self.current_time:
            return 0
        return max(0, self.current_time - process.arrival_time)

    def adaptive_feedback(self) -> tuple[str, str, str]:
        # Provide a simple recommendation based on the current workload shape.
        arrived = [p for p in self.processes if p.arrival_time <= self.current_time and not p.is_completed]
        metrics = self.metrics()
        completed = [p for p in self.processes if p.completion_time is not None]
        ready_count = len(self.ready_processes())
        bursts = [p.burst_time for p in self.processes]
        mixed = bursts and max(bursts) >= 2.2 * max(1, min(bursts)) and len(bursts) >= 3
        short_jobs = len([burst for burst in bursts if burst <= 4])
        long_jobs = len([burst for burst in bursts if burst >= 7])

        if not self.processes:
            return (
                "Workload Waiting",
                "Recommendation: Add processes.\n\nReason: No workload is available, so waiting time, utilization, and fairness cannot be evaluated yet.",
                "#94A3B8",
            )

        if completed and len(completed) == len(self.processes):
            if mixed:
                best = "MLFQ"
                reason = f"The workload mixed {short_jobs} short jobs with {long_jobs} long CPU-bound jobs. MLFQ keeps short jobs responsive while long jobs continue in lower queues."
            elif metrics["avg_response"] >= 5 and self.algorithm in {"FCFS", "SJF Non-Preemptive", "Priority Non-Preemptive"}:
                best = "Round Robin or SRTF"
                reason = "The final response time is high for an interactive workload, so a preemptive scheduler would let new arrivals receive CPU time earlier."
            elif metrics["avg_waiting"] >= 8:
                best = "Round Robin"
                reason = "The final waiting time is high, so time slicing improves fairness among ready processes."
            elif self.algorithm == "MLFQ":
                best = "MLFQ"
                reason = "The current MLFQ result is stable and remains suitable for mixed interactive and CPU-bound workloads."
            else:
                best = "SJF Non-Preemptive"
                reason = "The workload behaves like a small batch workload, so shortest-job ordering keeps average waiting time low."
            return (
                "Workload Complete",
                f"Recommendation: {best} for the next similar workload.\n\nEvidence: Average waiting = {metrics['avg_waiting']:.2f}, response = {metrics['avg_response']:.2f}, CPU utilization = {metrics['cpu_utilization']:.1f}%.\n\nReason: {reason}",
                "#2EE59D",
            )

        if arrived:
            starved = max(arrived, key=lambda p: self.live_waiting_time(p))
            starved_wait = self.live_waiting_time(starved)
            if starved_wait >= max(10, self.aging_threshold * 2):
                return (
                    "Starvation Risk",
                    f"Recommendation: MLFQ with aging.\n\nEvidence: {starved.pid} has waited {starved_wait} time units while other work continued.\n\nReason: MLFQ aging promotes long-waiting processes, so no process remains ignored indefinitely.",
                    "#FFB703",
                )

        if mixed and self.algorithm != "MLFQ":
            return (
                "Mixed Workload",
                f"Recommendation: MLFQ.\n\nEvidence: The workload has {short_jobs} short/interactive jobs and {long_jobs} long CPU-bound jobs.\n\nReason: MLFQ gives quick service to short jobs and gradually demotes CPU-heavy jobs to lower queues.",
                "#38BDF8",
            )
        if metrics["avg_waiting"] >= 8 and self.algorithm not in {"Round Robin", "MLFQ"}:
            return (
                "High Waiting Time",
                f"Recommendation: Round Robin with quantum {self.rr_quantum}, or MLFQ for adaptive fairness.\n\nEvidence: Average waiting time is {metrics['avg_waiting']:.2f} across arrived processes.\n\nReason: Preemption gives waiting jobs more frequent CPU access.",
                "#FB7185",
            )
        if metrics["cpu_utilization"] < 45 and self.current_time > 5 and ready_count == 0:
            return (
                "Low CPU Utilization",
                f"Recommendation: Add more processes or reduce large arrival gaps.\n\nEvidence: CPU utilization is {metrics['cpu_utilization']:.1f}% and the ready queue is empty.\n\nReason: The CPU is idle because no process is ready, not because the selected algorithm is unfair.",
                "#A3E635",
            )
        if metrics["avg_response"] >= 5 and self.algorithm not in {"SRTF", "Round Robin", "MLFQ"}:
            return (
                "Slow First Response",
                f"Recommendation: SRTF or MLFQ.\n\nEvidence: Average response time is {metrics['avg_response']:.2f} time units.\n\nReason: Preemptive scheduling reduces the delay before a newly arrived process first receives CPU time.",
                "#C084FC",
            )
        return (
            "System Balanced",
            f"Recommendation: Continue with {self.algorithm}.\n\nEvidence: Waiting, response, and fairness indicators are acceptable for the current workload.\n\nReason: No starvation or severe mixed-workload penalty is detected.",
            "#2EE59D",
        )

