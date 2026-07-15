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




## Section 3: Multi-Tenant Data Isolation

### Async Failure Modes and ContextVars
**The Failure Mode:** Standard synchronous Django uses a "Thread-per-Request" model, making `threading.local()` safe for storing tenant state. However, in an Asynchronous environment, a single event loop thread handles multiple concurrent requests. If we use thread-local storage in async, context switching will cause data to be overwritten mid-request. For example, if Tenant A and Tenant B make simultaneous requests, the single thread might overwrite Tenant A's thread-local ID with Tenant B's ID, resulting in catastrophic cross-tenant data leaks.

**The Solution:** Anticipating this failure mode, I bypassed `threading.local()` entirely and built my solution using Python's modern **`contextvars`** library from the beginning. `contextvars` natively supports asynchronous execution by attaching the data directly to the execution context (the specific task/request) rather than the OS thread. This guarantees that even under heavy async concurrency, the tenant state remains perfectly isolated.




## Section 4: Written Architecture Review

### Question A: Django Admin Performance

If a client's Django admin page is loading slowly with 500,000+ records, a primary key index alone will not solve the issue. I would investigate and fix the following three root causes:

**1. The Foreign Key Dropdown Crash**
When the admin page loads a model that has a `ForeignKey` to another massive table, Django's default behavior is to render all 500,000+ related records into a single HTML `<select>` dropdown menu. This instantly freezes the browser and exhausts memory. To fix this, I would update the `ModelAdmin` configuration by defining `autocomplete_fields = ['foreign_key_field']` or `raw_id_fields = ['foreign_key_field']`. This replaces the heavy dropdown with an AJAX-powered search bar or a simple ID text input.

**2. The N+1 Query Problem in `list_display`**
If the admin's `list_display` includes a field from a related model (for example, `order.customer.name`), Django will run one initial query for the orders, and then a separate database query for every single row to fetch the customer name. To fix this, I would use the `list_select_related = ['customer']` mechanism in the `ModelAdmin`. This forces the ORM to use an SQL `JOIN` under the hood, fetching all related data in exactly one efficient query.

**3. The Pagination `COUNT(*)` Bottleneck**
By default, the Django admin paginator runs a `SELECT COUNT(*)` query to display the exact total number of records at the bottom of the page (e.g., "1 to 100 of 500,000"). On massive tables in databases like PostgreSQL, fetching an exact count requires a full table scan, which is extremely slow. To fix this, I would set the configuration `show_full_result_count = False` in the `ModelAdmin`. This disables the expensive exact count query, prioritizing speed over knowing the exact total.


### Question B: Pagination Trade-offs

When paginating an API with 10,000+ records, choosing between offset-based and cursor-based pagination fundamentally changes how the database and the client interact at scale.

**1. Offset-Based Pagination**
Offset pagination utilizes SQL commands like `LIMIT 100 OFFSET 5000`. 
* **Database Scan Behavior:** At scale, this introduces severe performance degradation. To fetch page 50, the database cannot simply jump to row 5000; it must sequentially scan and discard the first 5,000 rows before returning the next 100. This is an $O(N)$ operation that becomes progressively slower on deeper pages.
* **Data Mutation & Infinite Scroll:** If a user is on Page 1 and a new record is inserted into the database, all existing records shift down by one position. When the client requests Page 2, the last item from Page 1 will appear again as a duplicate. This creates a highly flawed UX for mobile infinite scroll. 

**2. Cursor-Based Pagination**
Cursor pagination relies on a stable, indexed reference point, such as `WHERE created_at < 'last_seen_timestamp' LIMIT 100`.
* **Database Scan Behavior:** This is an $O(1)$ operation. The database utilizes the index to jump instantly to the exact timestamp and fetches the next 100 rows without scanning previous records. Performance remains flat and lightning-fast regardless of depth.
* **Data Mutation & Infinite Scroll:** Because the query relies on a fixed marker rather than a relative position, new inserts do not shift the dataset. It prevents duplicate or skipped records, making it the industry standard for mobile app infinite scroll.

**The Choice:**
I would choose **Cursor-based pagination** for this API, especially if it feeds a mobile app or handles high-frequency writes. The only trade-off I am sacrificing is the ability for users to jump directly to arbitrary page numbers (e.g., clicking a "Page 15" button). If the endpoint was strictly for an internal admin dashboard where jumping to specific pages is a business requirement on static data, only then would I default to offset-based.