import graphene
from graphene_django.types import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from opencivicdata.core.models import (
    Jurisdiction,
    Organization, OrganizationIdentifier, OrganizationName,
    OrganizationLink, OrganizationSource,
    Person, PersonIdentifier, PersonName, PersonContactDetail, PersonLink,
    PersonSource,
    Post, Membership,
    # currently not supporting
    # (Post|Membership|Organization)(ContactDetail|Link)
)


# override default ID behavior w/ behavior that preserves OCD ids
class OCDNode(graphene.relay.Node):
    class Meta:
        name = 'Node'

    @staticmethod
    def to_global_id(type, id):
        return id

    @staticmethod
    def get_node_from_global_id(id, context, info, only_type=None):
        if id.startswith('ocd-jurisdiction'):
            return Jurisdiction.objects.get(id=id)
        elif id.startswith('ocd-organization'):
            return Person.objects.get(id=id)
        elif id.startswith('ocd-person'):
            return Person.objects.get(id=id)



class PostType(DjangoObjectType):
    class Meta:
        model = Post


class MembershipType(DjangoObjectType):
    class Meta:
        model = Membership


class OrganizationIdentifierType(DjangoObjectType):
    class Meta:
        model = OrganizationIdentifier


class OrganizationNameType(DjangoObjectType):
    class Meta:
        model = OrganizationName


class OrganizationLinkType(DjangoObjectType):
    class Meta:
        model = OrganizationLink


class OrganizationSourceType(DjangoObjectType):
    class Meta:
        model = OrganizationSource


class OrganizationNode(DjangoObjectType):
    class Meta:
        model = Organization
        filter_fields = ['id', 'name', 'classification']
        interfaces = (OCDNode, )


class PersonNode(DjangoObjectType):
    class Meta:
        model = Person
        filter_fields = {
            'name': ['exact', 'istartswith'],
            'id': ['exact'],
        }
        interfaces = (OCDNode, )


class PersonIdentifierType(DjangoObjectType):
    class Meta:
        model = PersonIdentifier


class PersonNameType(DjangoObjectType):
    class Meta:
        model = PersonName


class PersonContactType(DjangoObjectType):
    class Meta:
        model = PersonContactDetail


class PersonLinkType(DjangoObjectType):
    class Meta:
        model = PersonLink


class PersonSourceType(DjangoObjectType):
    class Meta:
        model = PersonSource

#### the good stuff ####

class JurisdictionNode(DjangoObjectType):
    class Meta:
        model = Jurisdiction
        interfaces = (OCDNode, )



class Query(graphene.ObjectType):
    jurisdiction = graphene.Field(JurisdictionNode,
                                  id=graphene.String(),
                                  name=graphene.String())

    def resolve_jurisdiction(self, info, id=None, name=None):
        if id:
            return Jurisdiction.objects.get(id=id)
        if name:
            return Jurisdiction.objects.get(name=name)
        else:
            raise ValueError("Jurisdiction requires id or name")


schema = graphene.Schema(query=Query)
