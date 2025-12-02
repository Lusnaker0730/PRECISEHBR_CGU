"""
FHIR Utilities
Shared utility functions for FHIR resource handling
"""
import logging


def get_observation_effective_date(resource):
    """
    Extract effective date from a FHIR Observation resource.
    
    Handles both effectiveDateTime and effectivePeriod.
    
    Args:
        resource: FHIR Observation resource (dict or object with as_json())
    
    Returns:
        ISO date string or '1900-01-01' if not found
    """
    # Handle both dict and fhirclient model objects
    if hasattr(resource, 'as_json'):
        resource = resource.as_json()
    
    if not isinstance(resource, dict):
        return '1900-01-01'
    
    # Try effectiveDateTime first
    if resource.get('effectiveDateTime'):
        return resource['effectiveDateTime']
    
    # Try effectivePeriod.start
    effective_period = resource.get('effectivePeriod', {})
    if effective_period.get('start'):
        return effective_period['start']
    
    return '1900-01-01'


def get_observation_effective_date_from_model(resource):
    """
    Extract effective date from a fhirclient model Observation.
    
    Args:
        resource: fhirclient Observation model object
    
    Returns:
        ISO date string or '1900-01-01' if not found
    """
    date_str = '1900-01-01'
    
    if hasattr(resource, 'effectiveDateTime') and resource.effectiveDateTime:
        if hasattr(resource.effectiveDateTime, 'isostring'):
            date_str = resource.effectiveDateTime.isostring
        else:
            date_str = str(resource.effectiveDateTime)
    elif hasattr(resource, 'effectivePeriod') and resource.effectivePeriod:
        if resource.effectivePeriod.start:
            if hasattr(resource.effectivePeriod.start, 'isostring'):
                date_str = resource.effectivePeriod.start.isostring
            else:
                date_str = str(resource.effectivePeriod.start)
    
    return date_str


def sort_observations_by_date(observations, descending=True):
    """
    Sort a list of FHIR Observation resources by effective date.
    
    Args:
        observations: List of FHIR Observation resources (dicts)
        descending: If True, most recent first (default)
    
    Returns:
        Sorted list of observation dicts
    """
    if not observations:
        return []
    
    dated_observations = []
    for obs in observations:
        date_str = get_observation_effective_date(obs)
        dated_observations.append((date_str, obs))
    
    dated_observations.sort(key=lambda x: x[0], reverse=descending)
    return [obs for _, obs in dated_observations]


def sort_bundle_entries_by_date(entries, descending=True):
    """
    Sort FHIR Bundle entries by their resource's effective date.
    
    Handles fhirclient model objects from search results.
    
    Args:
        entries: List of Bundle entries (with .resource attribute)
        descending: If True, most recent first (default)
    
    Returns:
        Sorted list of (date_string, resource) tuples
    """
    if not entries:
        return []
    
    sorted_entries = []
    for entry in entries:
        if not entry.resource:
            continue
        
        # Handle fhirclient model objects
        date_str = get_observation_effective_date_from_model(entry.resource)
        sorted_entries.append((date_str, entry.resource))
    
    sorted_entries.sort(key=lambda x: x[0], reverse=descending)
    return sorted_entries


def extract_most_recent_observation(entries):
    """
    Get the most recent observation from a list of Bundle entries.
    
    Args:
        entries: List of Bundle entries from a FHIR search
    
    Returns:
        Most recent resource as JSON dict, or None
    """
    sorted_entries = sort_bundle_entries_by_date(entries, descending=True)
    if sorted_entries:
        _, resource = sorted_entries[0]
        if hasattr(resource, 'as_json'):
            return resource.as_json()
        return resource
    return None

