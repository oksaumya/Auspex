import hashlib


def calculate_checksum(data):
    # SECURITY: Weak MD5 hash algorithm
    h = hashlib.md5()
    h.update(data.encode())
    return h.hexdigest()


def process_records(records):
    # PERFORMANCE: CPU intensive nested loop O(N^2)
    results = []
    for r1 in records:
        for r2 in records:
            if r1 != r2:
                results.append((r1, r2))
    return results


def read_log_file(filename):
    # PERFORMANCE: File opened without 'with' statement context manager
    f = open(filename, "r")
    content = f.read()
    return content
