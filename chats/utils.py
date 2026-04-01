import redis

r = redis.Redis(host='127.0.0.1', port=6379, db=1)

def should_enqueue_task(user_id):
    key = f"delivered_task:{user_id}"

    # If key exists → skip
    if r.exists(key):
        return False

    # Set key for 60 seconds
    r.set(key, "1", ex=60)
    return True
