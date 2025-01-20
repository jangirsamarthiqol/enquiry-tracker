import json
import tomli_w

def combine_service_accounts(json_files, output_toml):
    try:
        combined_data = {}
        
        # Iterate through all JSON files and add them to the combined dictionary
        for idx, json_file in enumerate(json_files, start=1):
            with open(json_file, 'r') as file:
                service_account_data = json.load(file)
                combined_data[f"service_account_{idx}"] = service_account_data
        
        # Write the combined data into a TOML file
        with open(output_toml, 'wb') as toml_file:
            tomli_w.dump(combined_data, toml_file)

        print(f"Successfully created combined TOML file: {output_toml}")
    except Exception as e:
        print(f"Error combining service accounts: {e}")

if __name__ == "__main__":

    service_account_files = ["service-account.json", "enquiry-tracking-153a65032a1b.json"]

    # Output TOML file
    output_toml_file = "combined-service-accounts.toml"

    # Combine JSON files into one TOML
    combine_service_accounts(service_account_files, output_toml_file)
