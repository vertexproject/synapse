# Notes on STIX 2.0 Examples

## General Comments
* Most of these were manually converted from the old [STIX 1.2 XML Idioms](http://stixproject.github.io/documentation/idioms/), and have been updated to STIX 2.0 JSON. This means many values are the same but some have been added based on required properties from the [STIX 2.0 Specification](https://docs.google.com/document/d/1yvqWaPPnPW-2NiVCLqzRszcx91ffMowfT5MmE9Nsy_w/edit#heading=h.8bbhgdisbmt).
* Some of the STIX 1.x idioms were scrapped when transitioning to STIX 2.0 since certain concepts did not translate well.
* All of these examples are placed within a STIX Bundle object.  
* There is a lot of repetition since all SDOs and SROs require common properties like: id, created, modified etc.
* The majority of these have indicators or specifically focus on indicators since this object was one of the main use cases for 2.0.
* Some older examples were taken out until 2.1 is finished. Examples for objects like Incidents, Infrastructure and Assets will return with the release of 2.1.
* In many cases, only required properties of objects were used unless the objective was to highlight specific objects as a whole. In those instances, most optional properties were also included.
* SROs in each of these examples are located at the bottom of the Bundle, after the SDOs.


## Comments for Individual Examples
* Detailed write-ups and analyses of these examples on the STIX 2.0 CTI-documentation site under the [Examples page](https://oasis-open.github.io/cti-documentation/stix/examples.html).

### Campaigns and Threat Actors
*Write-up on the documentation site to come soon*
* Completely rewritten from 1.x "Defining Campaigns vs. Threat Actors Idiom".
* Now includes Attack Pattern and multiple Identity objects.

### Identifying a Threat Actor Profile
* Description of this example can be seen on the CTI-documentation site [here](https://oasis-open.github.io/cti-documentation/examples/identifying-a-threat-actor-profile).
* Has been expanded from the 1.x idiom--added optional Threat Actor properties new to 2.0 such as aliases, roles, goals, motivation, and sophistication.

### Indicator for C2 IP Address
*Write-up on the documentation site to come soon*
* Needs to be expanded for 2.0--currently only contains one Indicator object representing the IP address.

### Indicator for Malicious URL
* Description of this example can be seen on the CTI-documentation site [here](https://oasis-open.github.io/cti-documentation/examples/indicator-for-malicious-url).
* This example was expanded upon for 2.0--a Malware SDO was added along with a relationship connecting it to the Indicator SDO.

### Indicator, Campaign, and Intrusion Set
*Write-up on the documentation site to come soon*
* Formerly titled Indictor to Campaign Relationship--expanded for 2.0 to include Intrusion Set SDO.

### Malicious E-mail Indicator With Attachment
*Write-up on the documentation site to come soon*
* Includes Attack Pattern and Identity objects not present in 1.x.

### Malware Indicator for File Hash
* Description of this example can be seen on the CTI-documentation site [here](https://oasis-open.github.io/cti-documentation/examples/malware-indicator-for-file-hash).
* Malware SDO is just a stub in 2.0, this example will be improved when 2.1 is released.

### Sighting of an Indicator
*Completely New Example Written for 2.0*
* Description of this example can be seen on the CTI-documentation site [here](https://oasis-open.github.io/cti-documentation/examples/sighting-of-an-indicator).

### Threat Actor Leveraging Attack Patterns and Malware
* Description of this example can be seen on the CTI-documentation site [here](https://oasis-open.github.io/cti-documentation/examples/threat-actor-leveraging-attack-patterns-and-malware).
* Expanded to demonstrate the use of Kill chains in STIX 2.0 within the Attack Pattern and Malware SDOs.

### Using Granular Markings
*Completely New Example Written for 2.0*

*Write-up on the documentation site to come soon*

### Using Marking Definitions
*Completely New Example Written for 2.0*
* Description of this example can be seen on the CTI-documentation site [here](https://oasis-open.github.io/cti-documentation/examples/using-marking-definitions).
* Demonstrates both specification-designed marking definition types: Statement and TLP.

### Infrastructure Examples
*Completely New Example Written for 2.1*
* This example contains the bundled form of the infrastructure examples from STIX 2.1 WD04.
* Demonstrates how to use the new Infrastructure object.
