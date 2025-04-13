from flask import Flask, request, jsonify
import uuid
import subprocess
import threading
import time

app = Flask(__name__)

# In-memory storage for registered nodes
nodes = {}
pods = {}
pod_counter = 0
last_heartbeat = {}
HEARTBEAT_TIMEOUT = 20  # seconds

@app.route('/add_node', methods=['POST'])
def add_node():
    data = request.get_json()
    cpu_cores = data.get('cpu_cores')

    if not cpu_cores or not isinstance(cpu_cores, int):
        return jsonify({"error": "Invalid CPU core value"}), 400

    node_id = str(uuid.uuid4())
    container_name = f"node_{node_id[:8]}"

    # Launch the node container
    subprocess.run(["docker", "run", "-d", "--name", container_name, "node-sim"])

    # Store node details with healthy status initially
    nodes[node_id] = {
        'cpu_cores': cpu_cores,
        'available_cpu': cpu_cores,
        'status': 'healthy',  # Set status to healthy
        'pods': [],
        'container_name': container_name
    }

    # Set the initial heartbeat time to current time
    last_heartbeat[node_id] = time.time()

    return jsonify({"message": "Node added", "node_id": node_id}), 200



@app.route('/list_nodes', methods=['GET'])
def list_nodes():
    return jsonify(nodes), 200


@app.route('/launch_pod', methods=['POST'])
def launch_pod():
    global pod_counter
    data = request.get_json()
    cpu_required = data.get('cpu_required')
    strategy = data.get('strategy', 'first-fit')  # default strategy

    if not cpu_required or not isinstance(cpu_required, int):
        return jsonify({'error': 'Invalid CPU value'}), 400

    node_id = schedule_pod(cpu_required, strategy)

    if node_id:
        pod_id = f"pod_{pod_counter}"
        pod_counter += 1

        node_data = nodes[node_id]
        node_data['available_cpu'] -= cpu_required
        node_data['pods'].append(pod_id)

        pods[pod_id] = {
            'cpu_required': cpu_required,
            'assigned_node': node_id
        }

        return jsonify({
            'message': f'Pod launched successfully using {strategy}',
            'pod_id': pod_id,
            'assigned_node': node_id
        }), 200

    return jsonify({'error': f'No suitable node found using {strategy}'}), 503

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json()
    node_id = data.get('node_id')

    if node_id not in nodes:
        return jsonify({"error": "Node not registered"}), 400

    # Update last heartbeat time
    last_heartbeat[node_id] = time.time()

    # Log the node's heartbeat reception
    print(f"[Heartbeat] Node {node_id} received. Status: {nodes[node_id]['status']}")

    # Confirm that the heartbeat was successfully received
    return jsonify({"message": "Heartbeat received"}), 200


def schedule_pod(cpu_required, strategy='first-fit'):
    selected_node_id = None

    if strategy == 'first-fit':
        for node_id, node_data in nodes.items():
            if node_data['status'] == 'healthy' and node_data['available_cpu'] >= cpu_required:
                return node_id

    elif strategy == 'best-fit':
        min_leftover = float('inf')
        for node_id, node_data in nodes.items():
            if node_data['status'] == 'healthy' and node_data['available_cpu'] >= cpu_required:
                leftover = node_data['available_cpu'] - cpu_required
                if leftover < min_leftover:
                    min_leftover = leftover
                    selected_node_id = node_id
        return selected_node_id

    elif strategy == 'worst-fit':
        max_available = -1
        for node_id, node_data in nodes.items():
            if node_data['status'] == 'healthy' and node_data['available_cpu'] >= cpu_required:
                if node_data['available_cpu'] > max_available:
                    max_available = node_data['available_cpu']
                    selected_node_id = node_id
        return selected_node_id

    return None


def health_monitor():
    while True:
        current_time = time.time()
        for node_id in list(nodes.keys()):
            last_seen = last_heartbeat.get(node_id, 0)
            
            # Log the time difference for debugging
            print(f"[HealthMonitor] Node {node_id} last seen at {last_seen}, current time: {current_time}")
            
            # Check if the node has been marked healthy and if it missed heartbeat timeout
            if nodes[node_id]['status'] == 'healthy' and current_time - last_seen > HEARTBEAT_TIMEOUT:
                print(f"[HealthMonitor] Node {node_id} FAILED! Last heartbeat {last_seen}, now {current_time}")
                nodes[node_id]['status'] = 'failed'
                print(f"[HealthMonitor] Node {node_id} status set to failed")

                # Reschedule its pods (if necessary)
                failed_pods = nodes[node_id]['pods']
                nodes[node_id]['pods'] = []
                nodes[node_id]['available_cpu'] = nodes[node_id]['cpu_cores']

                for pod_id in failed_pods:
                    pod_data = pods[pod_id]
                    cpu_required = pod_data['cpu_required']
                    rescheduled = False

                    for target_id, target_node in nodes.items():
                        if target_node['status'] == 'healthy' and target_node['available_cpu'] >= cpu_required:
                            target_node['available_cpu'] -= cpu_required
                            target_node['pods'].append(pod_id)
                            pod_data['assigned_node'] = target_id
                            rescheduled = True
                            print(f"[Rescheduler] Pod {pod_id} moved to Node {target_id}")
                            break

                    if not rescheduled:
                        print(f"[Rescheduler] Pod {pod_id} could NOT be rescheduled.")

            # Check if the node has failed and has a valid heartbeat
            elif nodes[node_id]['status'] == 'failed' and current_time - last_seen <= HEARTBEAT_TIMEOUT:
                # Update status back to healthy if heartbeat is received after timeout
                print(f"[HealthMonitor] Node {node_id} recovered! Last heartbeat {last_seen}, now {current_time}")
                nodes[node_id]['status'] = 'healthy'
                print(f"[HealthMonitor] Node {node_id} status set to healthy")

        time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=health_monitor, daemon=True).start()
    app.run(debug=True, port=5000)
