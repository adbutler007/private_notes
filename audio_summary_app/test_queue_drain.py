#!/usr/bin/env python3
"""
Test that queue draining logic works correctly
"""

import queue
import time
import threading

def test_queue_drain():
    """Test queue draining with timeout"""
    test_queue = queue.Queue()

    # Add some items
    for i in range(5):
        test_queue.put(f"item_{i}")

    print(f"Queue has {test_queue.qsize()} items")
    print("Testing drain logic...")

    # Drain logic (same as in stop_recording)
    max_wait_time = 5
    wait_start = time.time()

    def consumer():
        """Simulate consuming from queue"""
        while not test_queue.empty():
            item = test_queue.get()
            print(f"  Consuming: {item}")
            time.sleep(0.3)  # Simulate processing time

    # Start consumer
    consumer_thread = threading.Thread(target=consumer)
    consumer_thread.start()

    # Wait for queue to drain
    while not test_queue.empty() and (time.time() - wait_start) < max_wait_time:
        print(f"  Queue size: {test_queue.qsize()}")
        time.sleep(0.5)

    consumer_thread.join()

    elapsed = time.time() - wait_start
    print(f"\n✓ Queue drained in {elapsed:.1f}s")
    print(f"✓ Final queue size: {test_queue.qsize()}")

    if test_queue.empty():
        print("✓ TEST PASSED - Queue fully drained")
        return 0
    else:
        print("✗ TEST FAILED - Queue still has items")
        return 1

if __name__ == "__main__":
    exit(test_queue_drain())
