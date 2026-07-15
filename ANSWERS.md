## Section 1: Incident Investigation Log

Step 1: Check the logs and latency: It is mentioned that the api works fast and responds within ~80 ms but as soon as the load increases, like for the user with 200+ orders, it chokes and crawls to 30 seconds timeout. This indicates the issue is directly related to data volume scaling, i.e., it is a performance issue and not some syntax error, otherwise, it could have failed even for the low load queries.

Step 2: Check the infrastructure: Since the code was not changed, I would verify if the server itself is overloaded. For instance, the database CPU could be maxed out at 100%, or maybe the RAM is full or maybe the server itself is down. But, these are not the cases, so I rule out the server crash.

Step 3: Check the ORM and Database Queries (The Breakthrough): I would run a database query profiler, say django-silk, to see every query Django executes. I notice that user with 1 order hits 2 queries and another user with 200 orders, hits 201 queries. This confirms the query count scales linearly (O(N)) with the number of database records, verifying that it is the loop driven logic causing the database bottleneck. Simply, this means that instead of just 1 query which could serve the purpose, the server is making 201 queries for the same amount of orders, causing the problem.

Root Cause Identification: The root cause is the 'N+1' query problem. Basically, the view loads all 200 rows from the database (order = Order.objects.all()), which is the first query, and then to fetch the customer name (order.customer.name or order.product.title), it goes to the database once for each of the 200 orders, thus adding the database round-trip overhead. Also, since the code was not changed, the recent deployment likely exposed this hidden architectural flaw. Meaning, in the development stage, smaller dataset was used which didn't expose the bad code. But during deployment, a data migration included a large volume of data for production purpose. So, the code stayed the same but the data volume didn't, finally causing the API to crash.

NOTE: Profiler evidence proving the query count reduction from 201 to 1 is attached in the /evidence directory as evidence_before.png and evidence_after.png




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