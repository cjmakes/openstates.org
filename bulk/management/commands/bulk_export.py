import csv
import json
import datetime
import tempfile
import zipfile
import boto3
from django.core.management.base import BaseCommand
from django.db.models import F
from opencivicdata.legislative.models import (
    LegislativeSession,
    Bill,
    BillAbstract,
    BillAction,
    BillTitle,
    BillIdentifier,
    RelatedBill,
    BillSponsorship,
    BillDocument,
    BillVersion,
    BillDocumentLink,
    BillVersionLink,
    BillSource,
    VoteEvent,
    PersonVote,
    VoteCount,
    VoteSource,
)
from ...models import DataExport
from utils.common import abbr_to_jid


def export_csv(filename, data, zf):
    num = len(data)
    if not num:
        return
    headers = data[0].keys()

    with tempfile.NamedTemporaryFile("w") as f:
        print("writing", filename, num, "records")
        of = csv.DictWriter(f, headers)
        of.writeheader()
        of.writerows(data)
        f.flush()
        zf.write(f.name, filename)
    return num


def export_json(filename, data, zf):
    num = len(data)
    if not num:
        return

    with tempfile.NamedTemporaryFile("w") as f:
        print("writing", filename, num, "records")
        json.dump(data, f)
        f.flush()
        zf.write(f.name, filename)
    return num


def _docver_to_json(dv):
    return {
        "note": dv.note,
        "date": dv.date,
        "links": list(dv.links.values("url", "media_type")),
    }


def _vote_to_json(v):
    return {
        "identifier": v.identifier,
        "motion_text": v.motion_text,
        "motion_classification": v.motion_classification,
        "start_date": v.start_date,
        "result": v.result,
        "organization__classification": v.organization.classification,
        "counts": list(v.counts.values("option", "value")),
        "votes": list(v.votes.values("option", "voter_name")),
    }


def _bill_to_json(b):
    return {
        "id": b.id,
        "legislative_session": b.legislative_session.identifier,
        "jurisdiction_name": b.legislative_session.jurisdiction.name,
        "identifier": b.identifier,
        "title": b.title,
        "chamber": b.from_organization.classification,
        "classification": b.classification,
        "subject": b.subject,
        "abstracts": list(b.abstracts.values("abstract", "note", "date")),
        "other_titles": list(b.other_titles.values("title", "note")),
        "other_identifiers": list(
            b.other_identifiers.values("note", "identifier", "scheme")
        ),
        "actions": list(
            b.actions.values(
                "organization__name", "description", "date", "classification", "order"
            )
        ),
        # TODO: action related entities
        "related_bills": list(b.related_bills.values("related_bill_id")),
        "sponsors": list(b.sponsorships.values("name", "primary", "classification")),
        "documents": [_docver_to_json(d) for d in b.documents.all()],
        "versions": [_docver_to_json(d) for d in b.versions.all()],
        "sources": list(b.sources.values("url")),
        # votes
        "votes": [_vote_to_json(v) for v in b.votes.all()],
        # raw text
        "raw_text": b.searchable.raw_text if b.searchable else None,
        "raw_text_url": b.searchable.version_link.url
        if b.searchable.version_link
        else None,
    }


def export_session_csv(state, session):
    sobj = LegislativeSession.objects.get(
        jurisdiction_id=abbr_to_jid(state), identifier=session
    )
    bills = Bill.objects.filter(legislative_session=sobj).values(
        "id",
        "identifier",
        "title",
        "classification",
        "subject",
        session_identifier=F("legislative_session__identifier"),
        jurisdiction=F("legislative_session__jurisdiction__name"),
        organization_classification=F("from_organization__classification"),
    )

    if not bills.count():
        print(f"no bills for {state} {session}")
        return
    filename = f"{state}_{session}_csv.zip"
    zf = zipfile.ZipFile(filename, "w")
    ts = datetime.datetime.utcnow()
    zf.writestr(
        "README",
        f"""Open States Data Export

State: {state}
Session: {session}
Generated At: {ts}
CSV Format Version: 2.0
""",
    )

    export_csv(f"{state}/{session}/{state}_{session}_bills.csv", bills, zf)

    for Model, fname in (
        (BillAbstract, "bill_abstracts"),
        (BillTitle, "bill_titles"),
        (BillIdentifier, "bill_identifiers"),
        (BillAction, "bill_actions"),
        (BillSource, "bill_sources"),
        (RelatedBill, "bill_related_bills"),
        (BillSponsorship, "bill_sponsorships"),
        (BillDocument, "bill_documents"),
        (BillVersion, "bill_versions"),
    ):
        subobjs = Model.objects.filter(bill__legislative_session=sobj).values()
        export_csv(f"{state}/{session}/{state}_{session}_{fname}.csv", subobjs, zf)

    subobjs = BillDocumentLink.objects.filter(
        document__bill__legislative_session=sobj
    ).values()
    export_csv(
        f"{state}/{session}/{state}_{session}_bill_document_links.csv", subobjs, zf
    )
    subobjs = BillVersionLink.objects.filter(
        version__bill__legislative_session=sobj
    ).values()
    export_csv(
        f"{state}/{session}/{state}_{session}_bill_version_links.csv", subobjs, zf
    )

    # TODO: BillActionRelatedEntity

    # Votes
    votes = VoteEvent.objects.filter(legislative_session=sobj).values(
        "id",
        "identifier",
        "motion_text",
        "motion_classification",
        "start_date",
        "result",
        "organization_id",
        "bill_id",
        "bill_action_id",
        jurisdiction=F("legislative_session__jurisdiction__name"),
        session_identifier=F("legislative_session__identifier"),
    )
    export_csv(f"{state}/{session}/{state}_{session}_votes.csv", votes, zf)
    for Model, fname in (
        (PersonVote, "vote_people"),
        (VoteCount, "vote_counts"),
        (VoteSource, "vote_sources"),
    ):
        subobjs = Model.objects.filter(vote_event__legislative_session=sobj).values()
        export_csv(f"{state}/{session}/{state}_{session}_{fname}.csv", subobjs, zf)

    return filename


def export_session_json(state, session):
    sobj = LegislativeSession.objects.get(
        jurisdiction_id=abbr_to_jid(state), identifier=session
    )
    bills = [
        _bill_to_json(b)
        for b in Bill.objects.filter(legislative_session=sobj)
        .select_related(
            "legislative_session",
            "legislative_session__jurisdiction",
            "from_organization",
            "searchable",
        )
        .prefetch_related(
            "abstracts",
            "other_titles",
            "other_identifiers",
            "actions",
            "related_bills",
            "sponsorships",
            "documents",
            "documents__links",
            "versions",
            "versions__links",
            "sources",
            "votes",
            "votes__counts",
            "votes__votes",
        )
    ]
    filename = f"{state}_{session}_json.zip"
    zf = zipfile.ZipFile(filename, "w")
    ts = datetime.datetime.utcnow()
    zf.writestr(
        "README",
        f"""Open States Data Export

State: {state}
Session: {session}
Generated At: {ts}
JSON Format Version: 0.2
""",
    )

    export_json(f"{state}/{session}/{state}_{session}_bills.json", bills, zf)


def upload_and_publish(state, session, filename, data_type):
    sobj = LegislativeSession.objects.get(
        jurisdiction_id=abbr_to_jid(state), identifier=session
    )
    s3 = boto3.client("s3")

    BULK_S3_BUCKET = "data.openstates.org"
    s3_path = f"{data_type}/latest/"
    s3_url = f"https://{BULK_S3_BUCKET}/{s3_path}{filename}"

    s3.upload_file(
        filename, BULK_S3_BUCKET, s3_path + filename, ExtraArgs={"ACL": "public-read"}
    )
    print("uploaded", s3_url)
    obj, created = DataExport.objects.update_or_create(
        session=sobj, defaults=dict(url=s3_url), data_type="csv"
    )


class Command(BaseCommand):
    help = "export data as CSV"

    def add_arguments(self, parser):
        parser.add_argument("state")
        parser.add_argument("sessions", nargs="*")
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--format")

    def handle(self, *args, **options):
        data_type = options["format"]
        if data_type not in ("csv", "json"):
            raise ValueError("--format must be csv or json")
        state = options["state"]
        sessions = [
            s.identifier
            for s in LegislativeSession.objects.filter(
                jurisdiction_id=abbr_to_jid(state)
            )
        ]
        if options["all"]:
            options["sessions"] = sessions
        if not options["sessions"]:
            print("available sessions:")
            for session in sessions:
                print("    ", session)
        else:
            for session in options["sessions"]:
                if session in sessions:
                    if data_type == "csv":
                        filename = export_session_csv(state, session)
                    else:
                        filename = export_session_json(state, session)
                    if filename:
                        upload_and_publish(state, session, filename, data_type)
