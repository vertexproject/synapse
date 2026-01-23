"""
Base schema for Synapse model definitions using dataclasses.

This module provides dataclass models derived from synapse.models.base,
converted to a schema style compatible with llama_index patterns.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import IntEnum
from hashlib import sha256
from typing import Any


# =============================================================================
# Enumerations
# =============================================================================

class Sophistication(IntEnum):
    """
    A sophistication score enumeration.

    Used to indicate the sophistication level of threat actors,
    techniques, or other entities.
    """
    VERY_LOW = 10
    LOW = 20
    MEDIUM = 30
    HIGH = 40
    VERY_HIGH = 50


class Priority(IntEnum):
    """
    A generic priority enumeration.

    Used for meta:priority, meta:activity, and meta:severity types.
    """
    NONE = 0
    LOWEST = 10
    LOW = 20
    MEDIUM = 30
    HIGH = 40
    HIGHEST = 50


# Aliases for semantic clarity
Activity = Priority
Severity = Priority


# =============================================================================
# Base Classes
# =============================================================================

@dataclass
class BaseComponent:
    """
    Base component object to capture class names.

    Provides serialization helpers and class name injection for
    robust serialization/deserialization.
    """

    @classmethod
    def class_name(cls) -> str:
        """
        Get the class name, used as a unique ID in serialization.

        This provides a key that makes serialization robust against actual class
        name changes.
        """
        return cls.__name__

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """Convert to dictionary with class name."""
        data = asdict(self)
        data['class_name'] = self.class_name()
        return data

    def to_json(self, **kwargs: Any) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(**kwargs), default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any], **kwargs: Any) -> BaseComponent:
        """Create instance from dictionary."""
        data = dict(data)
        data.pop('class_name', None)
        if kwargs:
            data.update(kwargs)
        return cls(**data)

    @classmethod
    def from_json(cls, data_str: str, **kwargs: Any) -> BaseComponent:
        """Create instance from JSON string."""
        data = json.loads(data_str)
        return cls.from_dict(data, **kwargs)


@dataclass
class GuidNode(BaseComponent):
    """
    Base class for GUID-identified nodes.

    Most Synapse forms use GUIDs as primary keys.
    """
    guid: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def hash(self) -> str:
        """Generate a hash representing the state of the node."""
        doc_identity = self.to_json()
        return sha256(doc_identity.encode('utf-8', 'surrogatepass')).hexdigest()


# =============================================================================
# Taxonomy Interface
# =============================================================================

@dataclass
class TaxonomyNode(GuidNode):
    """
    Properties common to taxonomies.

    This is the dataclass equivalent of the meta:taxonomy interface.
    Taxonomy nodes form hierarchical classification structures.
    """
    title: str | None = None
    """A brief title of the definition."""

    summary: str | None = None
    """Deprecated. Please use title/desc."""

    desc: str | None = None
    """A definition of the taxonomy entry."""

    sort: int | None = None
    """A display sort order for siblings."""

    base: str | None = None
    """The base taxon."""

    depth: int | None = None
    """The depth indexed from 0."""

    parent: str | None = None
    """The taxonomy parent (self-referential)."""


# =============================================================================
# Taxonomy Type Definitions
# =============================================================================

@dataclass
class MetaFeedTypeTaxonomy(TaxonomyNode):
    """A data feed type taxonomy."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:feed:type:taxonomy'


@dataclass
class MetaNoteTypeTaxonomy(TaxonomyNode):
    """An analyst note type taxonomy."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:note:type:taxonomy'


@dataclass
class MetaTimelineTaxonomy(TaxonomyNode):
    """A taxonomy of timeline types for meta:timeline nodes."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:timeline:taxonomy'


@dataclass
class MetaEventTaxonomy(TaxonomyNode):
    """A taxonomy of event types for meta:event nodes."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:event:taxonomy'


@dataclass
class MetaRulesetTypeTaxonomy(TaxonomyNode):
    """A taxonomy for meta:ruleset types."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:ruleset:type:taxonomy'


@dataclass
class MetaRuleTypeTaxonomy(TaxonomyNode):
    """A taxonomy for meta:rule types."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:rule:type:taxonomy'


@dataclass
class MetaAggregateTypeTaxonomy(TaxonomyNode):
    """A type of item being counted in aggregate."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:aggregate:type:taxonomy'


# =============================================================================
# Core Model Definitions (Forms)
# =============================================================================

@dataclass
class MetaSource(GuidNode):
    """
    A data source unique identifier.

    Represents a source of data that can be referenced by other nodes
    to indicate provenance.
    """
    name: str | None = None
    """A human friendly name for the source."""

    type: str | None = None
    """An optional type field used to group sources."""

    url: str | None = None
    """A URL which documents the meta source."""

    ingest_cursor: str | None = None
    """Used by ingest logic to capture the current ingest cursor within a feed."""

    ingest_latest: datetime | None = None
    """Used by ingest logic to capture the last time a feed ingest ran."""

    ingest_offset: int | None = None
    """Used by ingest logic to capture the current ingest offset within a feed."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:source'


@dataclass
class MetaSeen(BaseComponent):
    """
    Annotates that the data in a node was obtained from or observed by a given source.

    Deprecated: Use edge relationships instead.
    """
    source: str = ''
    """The source (meta:source GUID) which observed or provided the node."""

    node: str = ''
    """The node definition (ndef) which was observed by or received from the source."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:seen'


@dataclass
class MetaFeed(GuidNode):
    """
    A data feed provided by a specific source.

    Represents a structured data feed from an external or internal source.
    """
    id: str | None = None
    """An identifier for the feed."""

    name: str | None = None
    """A name for the feed."""

    type: str | None = None
    """The type of data feed (meta:feed:type:taxonomy)."""

    source: str | None = None
    """The meta:source GUID which provides the feed."""

    url: str | None = None
    """The URL of the feed API endpoint."""

    query: str | None = None
    """The query logic associated with generating the feed output."""

    opts: dict[str, Any] | None = None
    """An opaque JSON object containing feed parameters and options."""

    period_start: datetime | None = None
    """Start of time window over which results have been ingested."""

    period_end: datetime | None = None
    """End of time window over which results have been ingested."""

    latest: datetime | None = None
    """The time of the last record consumed from the feed."""

    offset: int | None = None
    """The offset of the last record consumed from the feed."""

    cursor: str | None = None
    """A cursor used to track ingest offset within the feed."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:feed'


@dataclass
class MetaNote(GuidNode):
    """
    An analyst note about nodes linked with -(about)> edges.

    Provides a way to attach analyst commentary and observations to nodes.
    """
    type: str | None = None
    """The note type (meta:note:type:taxonomy)."""

    text: str | None = None
    """The analyst authored note text (supports markdown)."""

    author: str | None = None
    """The contact information (ps:contact) of the author."""

    creator: str | None = None
    """The synapse user who authored the note."""

    created: datetime | None = None
    """The time the note was created."""

    updated: datetime | None = None
    """The time the note was updated."""

    replyto: str | None = None
    """The note (meta:note GUID) this is a reply to."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:note'


@dataclass
class MetaTimeline(GuidNode):
    """
    A curated timeline of analytically relevant events.

    Provides a container for organizing related events in temporal order.
    """
    title: str | None = None
    """A title for the timeline."""

    summary: str | None = None
    """A prose summary of the timeline."""

    type: str | None = None
    """The type of timeline (meta:timeline:taxonomy)."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:timeline'


@dataclass
class MetaEvent(GuidNode):
    """
    An analytically relevant event in a curated timeline.

    Represents a discrete event within a timeline.
    """
    timeline: str | None = None
    """The timeline (meta:timeline GUID) containing the event."""

    title: str | None = None
    """A title for the event."""

    summary: str | None = None
    """A prose summary of the event."""

    time: datetime | None = None
    """The time that the event occurred."""

    index: int | None = None
    """The index of this event in a timeline without exact times."""

    duration: int | None = None
    """The duration of the event in milliseconds."""

    type: str | None = None
    """Type of event (meta:event:taxonomy)."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:event'


@dataclass
class MetaRuleset(GuidNode):
    """
    A set of rules linked with -(has)> edges.

    Container for organizing related rules together.
    """
    name: str | None = None
    """A name for the ruleset."""

    type: str | None = None
    """The ruleset type (meta:ruleset:type:taxonomy)."""

    desc: str | None = None
    """A description of the ruleset."""

    author: str | None = None
    """The contact information (ps:contact) of the ruleset author."""

    created: datetime | None = None
    """The time the ruleset was initially created."""

    updated: datetime | None = None
    """The time the ruleset was most recently modified."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:ruleset'


@dataclass
class MetaRule(GuidNode):
    """
    A generic rule linked to matches with -(matches)> edges.

    Represents detection or matching logic that can be applied to data.
    """
    name: str | None = None
    """A name for the rule."""

    type: str | None = None
    """The rule type (meta:rule:type:taxonomy)."""

    desc: str | None = None
    """A description of the rule."""

    text: str | None = None
    """The text of the rule logic."""

    author: str | None = None
    """The contact information (ps:contact) of the rule author."""

    created: datetime | None = None
    """The time the rule was initially created."""

    updated: datetime | None = None
    """The time the rule was most recently modified."""

    url: str | None = None
    """A URL which documents the rule."""

    ext_id: str | None = None
    """An external identifier for the rule."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:rule'


@dataclass
class MetaAggregate(GuidNode):
    """
    A node which represents an aggregate count of a specific type.

    Used for tracking counts and statistics.
    """
    type: str | None = None
    """The type of items being counted (meta:aggregate:type:taxonomy)."""

    time: datetime | None = None
    """The time that the count was computed."""

    count: int | None = None
    """The number of items counted in aggregate."""

    @classmethod
    def class_name(cls) -> str:
        return 'meta:aggregate'


# =============================================================================
# Deprecated Graph Types
# =============================================================================

@dataclass
class GraphCluster(GuidNode):
    """
    A generic node for clustering arbitrary nodes.

    Deprecated: Use more specific node types.
    """
    name: str | None = None
    """A human friendly name for the cluster."""

    desc: str | None = None
    """A human friendly long form description for the cluster."""

    type: str | None = None
    """An optional type field used to group clusters."""

    @classmethod
    def class_name(cls) -> str:
        return 'graph:cluster'


@dataclass
class GraphNode(GuidNode):
    """
    A generic node used to represent objects outside the model.

    Deprecated: Define specific node types instead.
    """
    type: str | None = None
    """The type name for the non-model node."""

    name: str | None = None
    """A human readable name for this record."""

    data: dict[str, Any] | None = None
    """Arbitrary non-indexed msgpack data attached to the node."""

    @classmethod
    def class_name(cls) -> str:
        return 'graph:node'


@dataclass
class GraphEvent(GuidNode):
    """
    A generic event node to represent events outside the model.

    Deprecated: Use MetaEvent instead.
    """
    time: datetime | None = None
    """The time of the event."""

    type: str | None = None
    """An arbitrary type string for the event."""

    name: str | None = None
    """A name for the event."""

    data: dict[str, Any] | None = None
    """Arbitrary non-indexed msgpack data attached to the event."""

    @classmethod
    def class_name(cls) -> str:
        return 'graph:event'


# =============================================================================
# Edge Definitions
# =============================================================================

@dataclass
class EdgeBase(BaseComponent):
    """
    Base class for edge (relationship) definitions.

    Edges represent directed relationships between nodes.
    """
    n1: str = ''
    """The source node definition (ndef)."""

    n1_form: str | None = None
    """The form type of the source node."""

    n2: str = ''
    """The target node definition (ndef)."""

    n2_form: str | None = None
    """The form type of the target node."""


@dataclass
class EdgeRefs(EdgeBase):
    """
    A digraph edge which records that N1 refers to or contains N2.

    Deprecated: Use lightweight edge syntax instead.
    """

    @classmethod
    def class_name(cls) -> str:
        return 'edge:refs'


@dataclass
class EdgeHas(EdgeBase):
    """
    A digraph edge which records that N1 has N2.

    Deprecated: Use lightweight edge syntax instead.
    """

    @classmethod
    def class_name(cls) -> str:
        return 'edge:has'


@dataclass
class EdgeWentTo(EdgeBase):
    """
    A digraph edge which records that N1 went to N2 at a specific time.

    Deprecated: Use lightweight edge syntax instead.
    """
    time: datetime | None = None
    """The time of the relationship."""

    @classmethod
    def class_name(cls) -> str:
        return 'edge:wentto'


@dataclass
class GraphEdge(EdgeBase):
    """
    A generic digraph edge to show relationships outside the model.

    Deprecated: Define specific edge types instead.
    """

    @classmethod
    def class_name(cls) -> str:
        return 'graph:edge'


@dataclass
class GraphTimeEdge(EdgeBase):
    """
    A generic digraph time edge to show relationships outside the model.

    Deprecated: Define specific edge types instead.
    """
    time: datetime | None = None
    """The time of the relationship."""

    @classmethod
    def class_name(cls) -> str:
        return 'graph:timeedge'


# =============================================================================
# Edge Relationship Types (Lightweight Edges)
# =============================================================================

class EdgeRelationship:
    """
    Lightweight edge relationship definitions.

    These define the valid edge verbs and their semantics.
    """
    # Generic edges
    REFS = 'refs'
    """The source node contains a reference to the target node."""

    LINKED = 'linked'
    """The source node is linked to the target node."""

    # Specific edges
    SEEN = 'seen'
    """meta:source observed the target node."""

    FOUND = 'found'
    """meta:feed produced the target node."""

    ABOUT = 'about'
    """meta:note is about the target node."""

    HAS = 'has'
    """meta:ruleset includes the rule."""

    MATCHES = 'matches'
    """meta:rule has matched on target node."""

    DETECTS = 'detects'
    """meta:rule is designed to detect the target."""

    GENERATED = 'generated'
    """meta:rule generated the target."""


# =============================================================================
# Type Aliases
# =============================================================================

# Node type union for type hints
MetaNodeType = (
    MetaSource |
    MetaFeed |
    MetaNote |
    MetaTimeline |
    MetaEvent |
    MetaRuleset |
    MetaRule |
    MetaAggregate
)

# Taxonomy type union
TaxonomyType = (
    MetaFeedTypeTaxonomy |
    MetaNoteTypeTaxonomy |
    MetaTimelineTaxonomy |
    MetaEventTaxonomy |
    MetaRulesetTypeTaxonomy |
    MetaRuleTypeTaxonomy |
    MetaAggregateTypeTaxonomy
)

# Edge type union
EdgeType = (
    EdgeRefs |
    EdgeHas |
    EdgeWentTo |
    GraphEdge |
    GraphTimeEdge
)

# Markdown type alias
Markdown = str
