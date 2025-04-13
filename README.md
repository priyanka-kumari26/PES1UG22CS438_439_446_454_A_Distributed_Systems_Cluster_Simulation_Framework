# PES1UG22CS438_439_446_454_A_Distributed_Systems_Cluster_Simulation_Framework

This project simulates a lightweight Kubernetes-like cluster that manages nodes and pods. Built using Flask and Docker, it showcases key distributed systems concepts such as resource scheduling, fault tolerance, and health monitoring.

Node registration with CPU resource allocation.
Pod deployment with configurable CPU requirements.
Heartbeat-based health monitoring and fault detection.
Automatic pod rescheduling on node failure.
Multiple scheduling strategies such as First-Fit, Best-Fit, Worst-Fit

# Creating the environment
python3 -m venv venv
source venv/bin/activate

# Install all teh requirements
pip install requirements.txt

# Run the server
cd api_server
python server.py

# Build Docker Image for Node Simulation
docker build -t node-sim .

# Add Node (Launches Docker Container)
curl -X POST http://localhost:5000/add_node -H "Content-Type: application/json" -d '{"cpu_cores": 4}'

# Send Heartbeat
python heartbeat.py <node_id>

# Launch Pod
curl -X POST http://localhost:5000/launch_pod -H "Content-Type: application/json" -d '{"cpu_required": 2, "strategy": "first-fit"}'

# List Pod 
curl http://localhost:5000/list_nodes
