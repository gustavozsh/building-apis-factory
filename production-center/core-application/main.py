import requests
import json
import pandas as pd
import pytz
from google.oauth2.service_account import Credentials
from datetime import date, datetime, timedelta
from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud import secretmanager

# URN do cliente no linkedin
urn = 'urn:li:organization:511241'
urn_encoded = "urn%3Ali%3Aorganization%3A511241"
dataset_id = '...'
client_linkedin_name = "CLIENTE NAME"

def main():

    date_insertion = (
            datetime.now(pytz.timezone("America/Sao_Paulo")) - timedelta(2)
        ).strftime("%d-%m-%Y")

    #Alterar para a secret do cliente
    access_token = secret_google.get_secret(secret_name='linkedin_api')

    headers = {"Authorization": "Bearer " + access_token}

    # General page ok
    df_general = pd.DataFrame()
    df_general = get_linkedin.general(headers, urn, df_general, date_insertion)

    # Posts e analytics
    df_posts = pd.DataFrame()
    df_posts = get_linkedin.get_posts(date_insertion, df_posts, access_token, urn_encoded, urn)

    df_general = import_bq.to_string(df_general)
    df_posts = import_bq.to_string(df_posts)

    import_bq.to_bq(df_general, "bronze_linkedin_general")
    import_bq.to_bq(df_posts, "bronze_linkedin_posts")

class get_linkedin():

    def general(headers, urn, df, date_insertion):

        company_info_url = "https://api.linkedin.com/v2/organizationalEntityAcls?q=roleAssignee&role=ADMINISTRATOR&state=APPROVED&projection=(elements*(organizationalTarget~(localizedName)))"
        company_info = requests.get(company_info_url, headers=headers)
        company_info = json.loads(company_info._content.decode("utf-8"))
        
        for element in company_info["elements"]:
            if element["organizationalTarget~"]["localizedName"] == client_linkedin_name:
                id_org = element["organizationalTarget"]
                client = element["organizationalTarget~"]["localizedName"]
                break
    
        followers = requests.get("https://api.linkedin.com/v2/networkSizes/"+urn+"?edgeType=CompanyFollowedByMember", headers=headers)
        followers = json.loads(followers._content.decode("utf-8"))
        followers = followers["firstDegreeSize"]

        new_row = pd.Series({
                "date_insertion": date_insertion,
                "id": id_org,
                "client": client,
                "followers": followers
            })

        df = pd.concat([df, new_row.to_frame().T], ignore_index=True)
        return df

    def get_posts(date_insertion, df, token, urn_encoded, urn):

        headers = {"Authorization": "Bearer " + token,
                'X-Restli-Protocol-Version':'2.0.0'
                }

        # Alterar o COUNTA para quantidade de posts retroativos que precisa.
        response = requests.get("https://api.linkedin.com/v2/ugcPosts?q=authors&authors=List("+urn_encoded+")&sortBy=CREATED&count=40", headers=headers)
        response = json.loads(response._content.decode("utf-8"))

        for elements in response["elements"]:
            
            author = elements["author"]
            id = elements["id"]
            created = elements["created"]["time"]
            created = datetime.fromtimestamp(created/1000.0).date()
            post_type = elements["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"]
            text = elements["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"]
            text = text.replace('\n', ' ').replace('\r', '')
            try:
                thumbnail_url = elements["specificContent"]["com.linkedin.ugc.ShareContent"]["media"][0]["originalUrl"]
            except:
                thumbnail_url = ""
            url = "https://www.linkedin.com/embed/feed/update/"+id

            headers_analytics = {"Authorization": "Bearer " + token}
            
            if "share" in id:
                posts_analytics = requests.get("https://api.linkedin.com/v2/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity="+urn+"&shares[0]="+id, headers=headers_analytics)
                print(posts_analytics)
            else:
                posts_analytics = requests.get("https://api.linkedin.com/v2/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity="+urn+"&ugcPosts[0]="+id, headers=headers_analytics)
                print(posts_analytics)

            if posts_analytics.status_code == 200:

                posts_analytics = json.loads(posts_analytics._content.decode("utf-8"))

                uniqueImpressionsCount = posts_analytics["elements"][0]["totalShareStatistics"]["uniqueImpressionsCount"]
                sharecount = posts_analytics["elements"][0]["totalShareStatistics"]["shareCount"]
                engagement = posts_analytics["elements"][0]["totalShareStatistics"]["engagement"]
                clickcount = posts_analytics["elements"][0]["totalShareStatistics"]["clickCount"]
                likeCount = posts_analytics["elements"][0]["totalShareStatistics"]["likeCount"]
                impressioncount = posts_analytics["elements"][0]["totalShareStatistics"]["impressionCount"]
                commentcount = posts_analytics["elements"][0]["totalShareStatistics"]["commentCount"]

                new_row = pd.Series({
                    "date_insertion": date_insertion,
                    "author": author,
                    "created": created,
                    "post_id": id,
                    "post_type": post_type,
                    "text": text,
                    "thumbnail_url": thumbnail_url,
                    "url": url,
                    "uniqueImpressionsCount": uniqueImpressionsCount,
                    "sharecount": sharecount,
                    "engagement": engagement,
                    "clickcount": clickcount,
                    "likeCount": likeCount,
                    "impressioncount": impressioncount,
                    "commentcount": commentcount,
                })

                df = pd.concat([df, new_row.to_frame().T], ignore_index=True)

        return df

class secret_google():

    def get_secret(secret_name):

        cred = service_account.Credentials.from_service_account_file("../../keys/API.json")

        client = secretmanager.SecretManagerServiceClient(credentials=cred)
        name = f"projects/483180728332/secrets/{secret_name}/versions/1"
        response = client.access_secret_version(name=name)
        if "linkedin" in secret_name:
            key_dict = response.payload.data.decode("UTF-8")
        else:
            key_dict = json.loads(response.payload.data.decode("UTF-8"))
        return key_dict
    
class import_bq:
    def to_string(df):

        for column in df:
            df[column] = df[column].astype("string")

        return df

    def to_bq(d_frame, table_name):

        credentials = service_account.Credentials.from_service_account_info(secret_google.get_secret(secret_name='Acesso_BQ'))

        # Configura o cliente do BigQuery
        bigquery_client = bigquery.Client(credentials=credentials)

        # Configura o ID do dataset e da tabela do BigQuery
        table_id = table_name
        
        # Obtém a referência para a tabela existente
        table_ref = bigquery_client.dataset(dataset_id).table(table_id)
        table = bigquery_client.get_table(table_ref)
        
        # Atualiza a tabela com a nova contagem de usuários únicos
        bigquery_client.load_table_from_dataframe(d_frame, table)
        print("Tabela importada: "+str(table_name))

teste = main()