from pathlib import Path

from apiclient import discovery  # type: ignore
from httplib2 import Http
from oauth2client import client, file, tools  # type: ignore

SCOPES = "https://www.googleapis.com/auth/forms.body"
DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"
NEW_FORM = {
    "info": {
        "title": "Collaborative team",
    }
}
CSV = Path("riders.csv")


def post_form() -> None:
    store = file.Storage("token.json")
    creds = None
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets("auth.json", SCOPES)
        creds = tools.run_flow(flow, store)

    form_service = discovery.build(
        "forms",
        "v1",
        http=creds.authorize(Http()),
        discoveryServiceUrl=DISCOVERY_DOC,
        static_discovery=False,
    )

    requests = []
    i = 0
    names = []
    for line in CSV.read_text().split("\n"):
        name, _, _, _, _ = line.split(",")
        names.append(name)
    names.sort()
    for name in names:
        requests.append(
            {
                "createItem": {
                    "item": {
                        "title": name,
                        "questionItem": {
                            "question": {
                                "required": True,
                                "scaleQuestion": {
                                    "low": 1,
                                    "high": 10,
                                },
                            }
                        },
                    },
                    "location": {"index": i},
                }
            }
        )
        i += 1

    new_question = {"requests": requests}
    result = form_service.forms().create(body=NEW_FORM).execute()
    form_service.forms().batchUpdate(
        formId=result["formId"], body=new_question
    ).execute()
    form_service.forms().batchUpdate(
        formId=result["formId"],
        body={
            "requests": {
                "updateFormInfo": {
                    "info": {
                        "title": "Collaborative team",
                        "description": "Rate those riders on how much Velogames points they will score, regardless of their cost.\n1 is bad (<100 points), 10 is great (2000+ points).",
                    },
                    "updateMask": "*",
                }
            }
        },
    ).execute()
    get_result = form_service.forms().get(formId=result["formId"]).execute()
    print(get_result)
