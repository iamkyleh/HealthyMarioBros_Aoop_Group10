import matplotlib.pyplot as plt

def read_log(filename):
    times = []
    values = []
    with open(filename, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 2:
                continue  # skip malformed lines
            time_ms, val_str = parts
            times.append(float(time_ms) / 1000.0)  # convert millis → seconds
            values.append(float(val_str))
    return times, values

# Read both logs
server_times, server_vals = read_log("flag_log_server.txt")
client_times, client_vals = read_log("flag_log_client.txt")

# Take the first server time as STARTTIME
STARTTIME = server_times[0]

# Normalize times by subtracting STARTTIME
server_times = [t - STARTTIME for t in server_times]
client_times = [t - STARTTIME for t in client_times]

# Plot
plt.figure(figsize=(10,6))
plt.plot(server_times, server_vals, label="Server", color="blue")
plt.plot(client_times, client_vals, label="Client", color="red")

plt.xlabel("Time since STARTTIME (seconds)")
plt.ylabel("Value")
plt.title("Flag Log Comparison: Server vs Client (Normalized)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
