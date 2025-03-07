import pandas as pd
import requests

def filter_in_lexique(isol_root: str, isol_instances:str = "instances.csv"):
    
    instances = pd.read_csv(f'{isol_root}/{isol_instances}')

    # Get unique values in pandas column
    unique_signes = instances['sign'].unique()
    in_lexique = []

    for sign in unique_signes:

        api_call = f"https://dico.corpus-lsfb.be/api/annotation/gloss/{sign}"
        response = requests.get(api_call)

        if response.status_code == 200:
            in_lexique.append(sign)

    #Filter pandas dataframe
    instances_in_lexique = instances[instances['sign'].isin(in_lexique)]
    instances_in_lexique.to_csv(f'{isol_root}/instance_in_lexique.csv', index=False)


    




