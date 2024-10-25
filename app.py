from flask import Flask, request, jsonify, render_template
import re
import requests
import subprocess
import certifi
import os

app = Flask(__name__)

# Global variables to store contract details
contract_address = None
language_version = None
etherscan_api_key = "YCHKR939XKSGFK8C11M7MCDBQU6EM6CR9A"

# Route for the home page
@app.route('/')
def home():
    return render_template('index.html')  # Passing data to HTML

# Route for the slither page
@app.route('/slither')
def slither():
    return render_template('slither.html')

# Route to handle contract details submission
@app.route('/submit_contract', methods=['POST'])
def submit_contract():
    global contract_address, language_version  # Declare global variables
    data = request.get_json()  # Get JSON data from the POST request
    contract_address = data['contractAddress']
    language_version = data['languageVersion']

    # Process the contract address and language version as needed
    print(f"Received contract address: {contract_address}")
    print(f"Received language version: {language_version}")

    try:
        # Change Solidity compiler version
        change_solc_version(language_version)

        # Fetch and save the contract source code
        source_code = get_contract_source_code(contract_address, etherscan_api_key)
        save_contract_to_file(source_code)

        # Run Slither audit and save the report to a file
        run_slither_audit('contract.sol', 'audit_report.txt')
        
        return jsonify({'message': 'Contract details received and audit completed successfully!'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500  # Handle errors and return a response

# Function to change Solidity compiler version using solc-select
def change_solc_version(version):
    try:
        # Install the specified version if not already installed
        install_result = subprocess.run(['solc-select', 'install', version], check=False, capture_output=True, text=True)
        if "already installed" not in install_result.stdout:
            print(f"Solidity version {version} installed successfully.")

        # Use the specified version
        use_result = subprocess.run(['solc-select', 'use', version], check=True, capture_output=True, text=True)
        print(f"Switched to Solidity version {version}.")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while changing Solidity version: {e}")
        raise Exception(f"Failed to switch to Solidity version {version}")

def get_contract_source_code(contract_address, etherscan_api_key):
    url = f"https://api.etherscan.io/api"
    params = {
        "module": "contract",
        "action": "getsourcecode",
        "address": contract_address,
        "apikey": etherscan_api_key
    }
    response = requests.get(url, params=params, verify=certifi.where())
    data = response.json()

    if data['status'] == '1':  # Successful response
        return data['result'][0]['SourceCode']
    else:
        raise Exception("Error fetching contract source: " + data['result'])

def save_contract_to_file(source_code, filename='contract.sol'):
    with open(filename, 'w') as file:
        file.write(source_code)

def run_slither_audit(contract_filename, output_filename='audit_report.txt'):
    try:
        # Run Slither audit command
        result = subprocess.run(
            ['slither', contract_filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Check if there is output in stderr
        if result.stderr:
            # Replace 'INFO:Detectors:' with two new line characters
            formatted_output = re.sub(r'INFO:\s*Detectors:\s*', '\n\n **********ERRORS********** \n\n', result.stderr, flags=re.IGNORECASE)
        else:
            formatted_output = "No output found."

        # Save the formatted output to a txt file
        with open(output_filename, 'w') as file:
            file.write(formatted_output)

        print(f"Slither audit completed. Report saved to {output_filename}")
    except FileNotFoundError:
        print("Slither is not installed or not found in PATH.")
    except Exception as e:
        print(f"An error occurred while running Slither: {e}")

if __name__ == '__main__':
    app.run(debug=True)
