# cti-stix2-json-schemas

*This is an [OASIS TC Open Repository](https://www.oasis-open.org/resources/open-repositories/). See the [Governance](#governance) section for more information.*

This repository contains non-normative JSON schemas and examples for STIX 2. The examples include short examples of particular objects, more complete use-case examples, and complete reports in STIX 2. The repository contains both JSON schemas and JSON STIX documents.

**NOTE:** The schemas in this repository are intended to follow the [STIX 2.1 Specification](https://www.oasis-open.org/standards#stix2.0), but some requirements of the specification cannot be enforced in JSON schema alone. As a result, these schemas are insufficient to determine whether a particular example of STIX 2.1 JSON is "valid". Additionally, though care has been taken to ensure that these schemas do not conflict with the specification, in case of conflict, the specification takes precedence.

Some of the checks the schemas do not contain:

- The 'modified' property must be later or equal to 'created'.
- Marking Definitions (both object markings and granular markings) cannot refer to themselves (no circular refs).
- IDs for custom object types must start with the name of that type.
- Granular Marking selectors must refer to properties or items actually present in the object.
- Object references in the Cyber Observable layer must be valid within the local scope.
- Custom observable objects and observable extensions must have at least one custom property.
- Values for some Cyber Observable object properties must come from official registries (eg. artifact:mime_type must be a valid IANA MIME type).
- Some Cyber Observable objects' *_ref and *_refs properties must point to specific types of objects (eg. process:image_ref must point to an object of type 'file').
- In patterns, an Observation Expression MUST NOT have more than one Qualifier of a particular type.

**NOTE:** If you need schemas for previous versions of the STIX 2 specification, see the Git branch corresponding to that version.

## Governance

This GitHub public repository ( **[https://github.com/oasis-open/cti-stix2-json-schemas](https://github.com/oasis-open/cti-stix2-json-schemas)** ) was [proposed](https://lists.oasis-open.org/archives/cti/201608/msg00050.html) and [approved](https://www.oasis-open.org/committees/ballot.php?id=2961) [[bis](https://issues.oasis-open.org/browse/TCADMIN-2424)] by the the [OASIS Cyber Threat Intelligence (CTI) TC](https://www.oasis-open.org/committees/cti/) as an [OASIS TC Open Repository](https://www.oasis-open.org/resources/open-repositories/) to support development of open source resources related to Technical Committee work.

While this TC Open Repository remains associated with the sponsor TC, its development priorities, leadership, intellectual property terms, participation rules, and other matters of governance are [separate and distinct](https://github.com/oasis-open/cti-stix2-json-schemas/blob/master/CONTRIBUTING.md#governance-distinct-from-oasis-tc-process) from the OASIS TC Process and related policies.

All contributions made to this TC Open Repository are subject to open source license terms expressed in the [BSD-3-Clause License](https://www.oasis-open.org/sites/www.oasis-open.org/files/BSD-3-Clause.txt). That license was selected as the declared ["Applicable License"](https://www.oasis-open.org/resources/open-repositories/licenses) when the TC Open Repository was created.

As documented in ["Public Participation Invited](https://github.com/oasis-open/cti-stix2-json-schemas/blob/master/CONTRIBUTING.md#public-participation-invited)", contributions to this OASIS TC Open Repository are invited from all parties, whether affiliated with OASIS or not. Participants must have a GitHub account, but no fees or OASIS membership obligations are required. Participation is expected to be consistent with the [OASIS TC Open Repository Guidelines and Procedures](https://www.oasis-open.org/policies-guidelines/open-repositories), the open source [LICENSE](https://github.com/oasis-open/cti-stix2-json-schemas/blob/master/LICENSE) designated for this particular repository, and the requirement for an [Individual Contributor License Agreement](https://www.oasis-open.org/resources/open-repositories/cla/individual-cla) that governs intellectual property.

### <a id="maintainers">Maintainers</a>

TC Open Repository [Maintainers](https://www.oasis-open.org/resources/open-repositories/maintainers-guide) are responsible for oversight of this project's community development activities, including evaluation of GitHub [pull requests](https://github.com/oasis-open/cti-stix2-json-schemas/blob/master/CONTRIBUTING.md#fork-and-pull-collaboration-model) and [preserving](https://www.oasis-open.org/policies-guidelines/open-repositories#repositoryManagement) open source principles of openness and fairness. Maintainers are recognized and trusted experts who serve to implement community goals and consensus design preferences.

Initially, the associated TC members have designated one or more persons to serve as Maintainer(s); subsequently, participating community members may select additional or substitute Maintainers, per [consensus agreements](https://www.oasis-open.org/resources/open-repositories/maintainers-guide#additionalMaintainers).

**<a id="currentMaintainers">Current Maintainers of this TC Open Repository</a>**

 * [Chris Lenk](mailto:clenk@mitre.org); GitHub ID: [https://github.com/clenk](https://github.com/clenk); WWW: [MITRE](https://www.mitre.org)
 * [Jason Keirstead](mailto:Jason.Keirstead@ca.ibm.com); GitHub ID: [https://github.com/JasonKeirstead](https://github.com/JasonKeirstead); WWW: [IBM](http://www.ibm.com/)
 
## <a id="aboutOpenRepos">About OASIS TC Open Repositories</a>

 * [TC Open Repositories: Overview and Resources](https://www.oasis-open.org/resources/open-repositories/)
 * [Frequently Asked Questions](https://www.oasis-open.org/resources/open-repositories/faq)
 * [Open Source Licenses](https://www.oasis-open.org/resources/open-repositories/licenses)
 * [Contributor License Agreements (CLAs)](https://www.oasis-open.org/resources/open-repositories/cla)
 * [Maintainers' Guidelines and Agreement](https://www.oasis-open.org/resources/open-repositories/maintainers-guide)

## <a id="feedback">Feedback</a>

Questions or comments about this TC Open Repository's activities should be composed as GitHub issues or comments. If use of an issue/comment is not possible or appropriate, questions may be directed by email to the Maintainer(s) [listed above](#currentMaintainers). Please send general questions about TC Open Repository participation to OASIS Staff at [repository-admin@oasis-open.org](mailto:repository-admin@oasis-open.org) and any specific CLA-related questions to [repository-cla@oasis-open.org](mailto:repository-cla@oasis-open.org).
