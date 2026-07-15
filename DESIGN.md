## Section 2: Rate-Limited Async Job Queue Architecture

### Architecture Choice:

**Selection:** Celery + Redis

Evaluating the trade-offs for processing bursts of 2,000+ background tasks:

* **Custom Implementation:** Building a background worker from scratch using pure Python (`threading` or `asyncio`) is a bad practice in production. The trade-off is extreme maintenance overhead. Handling edge cases like mid-execution worker crashes or implementing robust exponential backoff for third-party rate limits requires hundreds of lines of complex, bug-prone code. It is better to use a mature system.

* **Django Q:** Django Q uses the primary SQL database as the message broker. The trade-off is heavy reliance on Disk I/O. Dropping thousands of tasks into a standard relational database concurrently will spike database CPU and degrade the performance of the main web application. Mixing persistent application data with ephemeral background tasks is a poor scaling practice.

* **Celery + Redis (Chosen):** Redis acts as an in-memory broker, meaning it stores task data entirely in RAM. It can ingest thousands of tasks in milliseconds without touching the hard drive, protecting the API's response time. Celery is chosen as the worker because of its built-in resilience: it natively handles exponential backoff for failed tasks and provides strict crash protection (detailed below).




### Rate Limiter Strategy

* **The Approach (Option C: Fixed Window):** I selected the Fixed Window approach utilizing native Redis commands (`INCR` and `EXPIRE`). While Token Bucket and Sliding Window provide smoother traffic shaping, the Fixed Window is chosen for its architectural simplicity and ultra-fast, $O(1)$ execution. It avoids the complex timestamp calculations of a Token Bucket and the constant database cleanup (`ZREMRANGEBYSCORE`) required by a Sliding Window.

* **The Trade-off (The Burst Flaw):** I am explicitly acknowledging the edge-case flaw of this approach. If the worker sends 200 emails at second 59, the Redis key expires at second 60, allowing the worker to instantly send another 200 emails at second 61. The third-party provider could detect a burst of 400 emails in a 2-second span, risking a ban. I am accepting this trade-off in favor of pipeline simplicity.

* **The Atomicity Guarantee:** To prevent race conditions, atomicity is guaranteed using a **Redis Pipeline**. By wrapping the `INCR` and `EXPIRE` commands in a single transaction block, Redis locks and executes both commands contiguously. This ensures a worker crash cannot leave an orphaned, permanently incremented counter in memory.

* **Redis Failure (Fail Closed):** If the Redis server crashes and the Celery worker cannot check the rate limit, the system is designed to **Fail Closed**. The worker will catch the connection error, pause execution, and retry the task later. I prioritize protecting the company's third-party API reputation over instant delivery. Yes, delayed emails are an annoyance, but a banned IP address is a catastrophe.


### Worker Crash Resilience (SIGKILL)

If a Celery worker process is forcefully terminated (`SIGKILL`) mid-execution, a standard configuration would result in a permanently lost task, as workers typically delete messages from the broker immediately upon receipt. 

To prevent this data loss, the worker is configured with `acks_late=True`. This setting mandates that Celery does not acknowledge the task (and therefore does not remove it from Redis) until the function successfully completes. If a worker crashes while sending an email, the unacknowledged task safely remains in the Redis queue, allowing a different worker to pick it up and execute it cleanly.



