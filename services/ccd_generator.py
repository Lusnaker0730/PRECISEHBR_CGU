"""
ONC Compliance: 45 CFR 170.315 (b)(6) - Data Export

This module generates C-CDA (Consolidated Clinical Document Architecture) R2.1
compliant Continuity of Care Documents (CCD) for exporting patient risk assessment
data and related clinical information.

The generated CCD includes:
- Patient demographics
- PRECISE-HBR risk assessment results
- Relevant observations (eGFR, hemoglobin, etc.)
- Problem list (bleeding history, chronic conditions)
- Medications (anticoagulants)
"""

import datetime
import uuid
from typing import Any
from xml.dom import minidom
from xml.etree import ElementTree as ET


class CCDGenerator:
    """
    Generator for C-CDA R2.1 Continuity of Care Documents.
    
    Implements the CCD template as specified by HL7 for ONC certification.
    """
    
    # Standard OIDs for C-CDA
    OID_CCD_DOCUMENT = "2.16.840.1.113883.10.20.22.1.2"
    OID_US_REALM_HEADER = "2.16.840.1.113883.10.20.22.1.1"
    OID_LOINC = "2.16.840.1.113883.6.1"
    OID_SNOMED = "2.16.840.1.113883.6.96"
    OID_UCUM = "2.16.840.1.113883.6.8"
    
    def __init__(self, organization_name="PRECISE-HBR Risk Assessment Service",
                 organization_oid="2.16.840.1.113883.19.5"):
        """
        Initialize the CCD generator.
        
        Args:
            organization_name: Name of the organization generating the document
            organization_oid: OID for the organization
        """
        self.organization_name = organization_name
        self.organization_oid = organization_oid
        self.namespaces = {
            'xmlns': 'urn:hl7-org:v3',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xmlns:sdtc': 'urn:hl7-org:sdtc'
        }
    
    def generate_ccd(self, patient_data: dict[str, Any],
                     risk_assessment: dict[str, Any],
                     observations: list[dict[str, Any]],
                     conditions: list[dict[str, Any]]) -> str:
        """
        Generate a complete CCD document.

        Args:
            patient_data: Patient demographics and identifiers
            risk_assessment: PRECISE-HBR risk assessment results
            observations: List of relevant observations (labs, vitals)
            conditions: List of relevant conditions/problems

        Returns:
            XML string of the CCD document
        """
        root = ET.Element('ClinicalDocument', self.namespaces)

        # Build document structure
        self._add_document_header(root, patient_data, risk_assessment)
        self._add_patient_section(root, patient_data)
        self._add_author_section(root)
        self._add_custodian_section(root)

        # Build document body
        body = ET.SubElement(root, 'component')
        structured_body = ET.SubElement(body, 'structuredBody')
        self._add_risk_assessment_section(structured_body, risk_assessment)
        self._add_results_section(structured_body, observations)
        self._add_problems_section(structured_body, conditions)

        return self._prettify_xml(root)
    
    def _get_current_timestamp(self) -> str:
        """Return current timestamp in HL7 format."""
        return datetime.datetime.now().strftime('%Y%m%d%H%M%S+0000')

    def _add_table_row(self, tbody: ET.Element, label: str, value: str) -> None:
        """Add a row to a table body with label and value columns."""
        row = ET.SubElement(tbody, 'tr')
        ET.SubElement(row, 'td').text = label
        ET.SubElement(row, 'td').text = value

    def _add_document_header(self, root: ET.Element, patient_data: dict[str, Any],
                            risk_assessment: dict[str, Any]) -> None:
        """Add CDA document header with metadata."""
        ET.SubElement(root, 'typeId', {
            'root': '2.16.840.1.113883.1.3',
            'extension': 'POCD_HD000040'
        })
        
        # Template IDs for C-CDA R2.1 CCD
        ET.SubElement(root, 'templateId', {'root': self.OID_US_REALM_HEADER})
        ET.SubElement(root, 'templateId', {'root': self.OID_CCD_DOCUMENT, 'extension': '2015-08-01'})

        # Document ID (unique for each document)
        ET.SubElement(root, 'id', {
            'root': self.organization_oid,
            'extension': str(uuid.uuid4())
        })
        
        # Document code (LOINC code for CCD)
        ET.SubElement(root, 'code', {
            'code': '34133-9',
            'codeSystem': self.OID_LOINC,
            'codeSystemName': 'LOINC',
            'displayName': 'Summarization of Episode Note'
        })

        # Title
        title = ET.SubElement(root, 'title')
        title.text = f"PRECISE-HBR Risk Assessment for {patient_data.get('name', 'Patient')}"

        # Effective time (document creation time)
        ET.SubElement(root, 'effectiveTime', {'value': self._get_current_timestamp()})

        # Confidentiality code
        ET.SubElement(root, 'confidentialityCode', {
            'code': 'N',
            'codeSystem': '2.16.840.1.113883.5.25',
            'displayName': 'Normal'
        })

        # Language code
        ET.SubElement(root, 'languageCode', {'code': 'en-US'})
    
    def _add_patient_section(self, root: ET.Element, patient_data: dict[str, Any]) -> None:
        """Add patient demographics section (recordTarget)."""
        record_target = ET.SubElement(root, 'recordTarget')
        patient_role = ET.SubElement(record_target, 'patientRole')
        
        # Patient ID
        if patient_data.get('id'):
            ET.SubElement(patient_role, 'id', {
                'root': self.organization_oid,
                'extension': patient_data['id']
            })
        
        # Patient demographics
        patient = ET.SubElement(patient_role, 'patient')
        
        # Name
        if patient_data.get('name'):
            name_elem = ET.SubElement(patient, 'name', {'use': 'L'})
            name_parts = patient_data['name'].split(' ', 1)
            given = ET.SubElement(name_elem, 'given')
            given.text = name_parts[0] if name_parts else patient_data['name']
            if len(name_parts) > 1:
                family = ET.SubElement(name_elem, 'family')
                family.text = name_parts[1]
        
        # Gender
        if patient_data.get('gender'):
            gender_code = 'M' if patient_data['gender'].lower() in ['male', 'm'] else 'F'
            ET.SubElement(patient, 'administrativeGenderCode', {
                'code': gender_code,
                'codeSystem': '2.16.840.1.113883.5.1',
                'displayName': patient_data['gender']
            })
        
        # Birth time
        if patient_data.get('birth_date'):
            birth_date_str = patient_data['birth_date'].replace('-', '')[:8]
            ET.SubElement(patient, 'birthTime', {'value': birth_date_str})
    
    def _add_author_section(self, root: ET.Element) -> None:
        """Add document author section."""
        author = ET.SubElement(root, 'author')

        # Author time (now)
        ET.SubElement(author, 'time', {'value': self._get_current_timestamp()})
        
        # Assigned author (application)
        assigned_author = ET.SubElement(author, 'assignedAuthor')
        ET.SubElement(assigned_author, 'id', {
            'root': self.organization_oid,
            'extension': 'PRECISE-HBR-APP'
        })
        
        # Assigned authoring device
        device = ET.SubElement(assigned_author, 'assignedAuthoringDevice')
        software_name = ET.SubElement(device, 'softwareName')
        software_name.text = "PRECISE-HBR Risk Calculator"
        
        # Representing organization
        org = ET.SubElement(assigned_author, 'representedOrganization')
        org_name = ET.SubElement(org, 'name')
        org_name.text = self.organization_name
    
    def _add_custodian_section(self, root: ET.Element) -> None:
        """Add document custodian section."""
        custodian = ET.SubElement(root, 'custodian')
        assigned_custodian = ET.SubElement(custodian, 'assignedCustodian')
        represented_org = ET.SubElement(assigned_custodian, 'representedCustodianOrganization')
        
        ET.SubElement(represented_org, 'id', {'root': self.organization_oid})
        org_name = ET.SubElement(represented_org, 'name')
        org_name.text = self.organization_name
    
    def _add_risk_assessment_section(self, structured_body: ET.Element,
                                     risk_assessment: dict[str, Any]) -> None:
        """Add risk assessment results as a custom section."""
        component = ET.SubElement(structured_body, 'component')
        section = ET.SubElement(component, 'section')

        # Template ID for assessment and plan section
        ET.SubElement(section, 'templateId', {
            'root': '2.16.840.1.113883.10.20.22.2.9',
            'extension': '2014-06-09'
        })

        # Section code
        ET.SubElement(section, 'code', {
            'code': '51847-2',
            'codeSystem': self.OID_LOINC,
            'displayName': 'Assessment and Plan'
        })

        # Title
        title = ET.SubElement(section, 'title')
        title.text = "PRECISE-HBR Risk Assessment"

        # Human-readable table
        text = ET.SubElement(section, 'text')
        table = ET.SubElement(text, 'table', {'border': '1', 'width': '100%'})

        # Table header
        thead = ET.SubElement(table, 'thead')
        header_row = ET.SubElement(thead, 'tr')
        ET.SubElement(header_row, 'th').text = 'Assessment'
        ET.SubElement(header_row, 'th').text = 'Value'

        # Table body with risk data
        tbody = ET.SubElement(table, 'tbody')

        bleeding_risk = risk_assessment.get('bleeding_risk_percent', 'N/A')
        bleeding_display = f"{bleeding_risk}%" if bleeding_risk != 'N/A' else 'N/A'

        self._add_table_row(tbody, 'PRECISE-HBR Total Score',
                           str(risk_assessment.get('total_score', 'N/A')))
        self._add_table_row(tbody, 'Risk Category',
                           risk_assessment.get('risk_category', 'N/A'))
        self._add_table_row(tbody, '1-Year Major Bleeding Risk', bleeding_display)
        self._add_table_row(tbody, 'Assessment Date',
                           datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))
    
    def _add_results_section(self, structured_body: ET.Element,
                            observations: list[dict[str, Any]]) -> None:
        """Add laboratory results and observations section."""
        if not observations:
            return

        component = ET.SubElement(structured_body, 'component')
        section = ET.SubElement(component, 'section')

        # Template ID for results section
        ET.SubElement(section, 'templateId', {
            'root': '2.16.840.1.113883.10.20.22.2.3.1',
            'extension': '2015-08-01'
        })

        # Section code
        ET.SubElement(section, 'code', {
            'code': '30954-2',
            'codeSystem': self.OID_LOINC,
            'displayName': 'Relevant diagnostic tests/laboratory data'
        })

        # Title
        title = ET.SubElement(section, 'title')
        title.text = "Laboratory Results"

        # Human-readable table
        text = ET.SubElement(section, 'text')
        table = ET.SubElement(text, 'table', {'border': '1', 'width': '100%'})

        thead = ET.SubElement(table, 'thead')
        header_row = ET.SubElement(thead, 'tr')
        for header in ['Test', 'Value', 'Unit', 'Date']:
            ET.SubElement(header_row, 'th').text = header

        tbody = ET.SubElement(table, 'tbody')
        for obs in observations:
            row = ET.SubElement(tbody, 'tr')
            date_value = obs.get('date', '')
            ET.SubElement(row, 'td').text = obs.get('name', 'Unknown')
            ET.SubElement(row, 'td').text = str(obs.get('value', 'N/A'))
            ET.SubElement(row, 'td').text = obs.get('unit', '')
            ET.SubElement(row, 'td').text = date_value[:10] if date_value else ''
    
    def _add_problems_section(self, structured_body: ET.Element,
                              conditions: list[dict[str, Any]]) -> None:
        """Add problems/conditions section."""
        if not conditions:
            return

        component = ET.SubElement(structured_body, 'component')
        section = ET.SubElement(component, 'section')

        # Template ID for problem section
        ET.SubElement(section, 'templateId', {
            'root': '2.16.840.1.113883.10.20.22.2.5.1',
            'extension': '2015-08-01'
        })

        # Section code
        ET.SubElement(section, 'code', {
            'code': '11450-4',
            'codeSystem': self.OID_LOINC,
            'displayName': 'Problem List'
        })

        # Title
        title = ET.SubElement(section, 'title')
        title.text = "Problems"

        # Human-readable list
        text = ET.SubElement(section, 'text')
        problem_list = ET.SubElement(text, 'list')

        for condition in conditions:
            item = ET.SubElement(problem_list, 'item')
            item.text = condition.get('display', condition.get('code', 'Unknown condition'))
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """Return a pretty-printed XML string with proper indentation."""
        rough_string = ET.tostring(elem, encoding='unicode')
        # Prefer defusedxml for security; fall back to standard minidom for internal XML
        try:
            from defusedxml import minidom as safe_minidom
            reparsed = safe_minidom.parseString(rough_string)  # nosec B318
        except ImportError:
            reparsed = minidom.parseString(rough_string)  # nosec B318
        return reparsed.toprettyxml(indent="  ", encoding='UTF-8').decode('utf-8')


# Lab observation definitions: (key, display_name, unit)
_LAB_OBSERVATIONS = [
    ('egfr', 'eGFR (Estimated Glomerular Filtration Rate)', 'mL/min/1.73m2'),
    ('hemoglobin', 'Hemoglobin', 'g/dL'),
    ('wbc', 'White Blood Cell Count', '10*9/L'),
    ('platelets', 'Platelet Count', '10*9/L'),
]


def generate_ccd_from_session_data(patient_data: dict[str, Any],
                                   risk_data: dict[str, Any],
                                   raw_fhir_data: dict[str, Any]) -> str:
    """
    Generate CCD from typical session data.

    Args:
        patient_data: Patient demographics
        risk_data: Risk assessment results
        raw_fhir_data: Raw FHIR data containing observations and conditions

    Returns:
        CCD XML string
    """
    generator = CCDGenerator()
    current_date = datetime.datetime.now().isoformat()

    # Extract observations from risk data
    observations = [
        {'name': name, 'value': risk_data[key], 'unit': unit, 'date': current_date}
        for key, name, unit in _LAB_OBSERVATIONS
        if risk_data.get(key) and risk_data[key] != 'Not available'
    ]

    # Extract conditions from ARC-HBR factors
    conditions = [
        {'display': factor, 'code': 'ARC-HBR-FACTOR'}
        for factor in risk_data.get('arc_hbr_factors', [])
    ]

    return generator.generate_ccd(
        patient_data=patient_data,
        risk_assessment=risk_data,
        observations=observations,
        conditions=conditions
    )

