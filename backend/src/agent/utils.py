from typing import Any, Dict, List
from langchain_core.messages import AnyMessage, AIMessage, HumanMessage


def get_research_topic(messages: List[AnyMessage]) -> str:
    """
    Get the research topic from the messages.
    """
    # check if request has a history and combine the messages into a single string
    if len(messages) == 1:
        research_topic = messages[-1].content
    else:
        research_topic = ""
        for message in messages:
            if isinstance(message, HumanMessage):
                research_topic += f"User: {message.content}\n"
            elif isinstance(message, AIMessage):
                research_topic += f"Assistant: {message.content}\n"
    return research_topic


def format_research_citations(sources_gathered: List[Dict]) -> str:
    """
    Format sources for inclusion in research prompt and create citation mapping.
    
    This function creates a structured reference list that can be included in the 
    LLM prompt, allowing the LLM to reference sources using [#N] notation.
    
    Args:
        sources_gathered: List of source dictionaries with 'value', 'short_url', 'label'
        
    Returns:
        str: Formatted source list for LLM prompt
    """
    if not sources_gathered:
        return ""
    
    formatted_sources = "\n\nAvailable Sources for Citation:\n"
    for idx, source in enumerate(sources_gathered, 1):
        value = source.get("value", "")
        label = source.get("label", "")
        short_url = source.get("short_url", "")
        
        # Determine source type and format appropriately
        if short_url.startswith("[KB-"):
            # Knowledge base source
            if label and not label.startswith("doc_"):
                filename = label.rsplit('.', 1)[0] if '.' in label else label
                source_desc = f"Knowledge Base Document: {filename}"
            else:
                source_desc = f"Knowledge Base: {value}"
        else:
            # Web source
            source_desc = f"Web Source: {label}" if label else f"Web Source: {value}"
        
        formatted_sources += f"[#{idx}] {source_desc}\n"
    
    formatted_sources += "\nPlease use [#N] notation to cite sources in your response.\n"
    return formatted_sources


def extract_pubmed_id_from_kb_path(kb_path: str) -> str:
    """
    Extract PubMed ID from knowledge base file path.
    
    Extracts PubMed ID from paths like:
    /root/autodl-fs/asd_firsts/extracted_markdown_files/markdown_batch_1749466568_22284798_auto_22284798.md
    
    Args:
        kb_path: File path containing PubMed ID
        
    Returns:
        str: PubMed ID if found, empty string otherwise
    """
    import re
    import os
    
    # Get filename from path
    filename = os.path.basename(kb_path)
    
    # Pattern to match PubMed ID: numbers between underscores, before _auto_
    # Looking for pattern like: _22284798_auto_
    pattern = r'_(\d+)_auto_\d+\.md$'
    match = re.search(pattern, filename)
    
    if match:
        return match.group(1)
    
    # Fallback: look for any number sequence before .md
    fallback_pattern = r'_(\d+)\.md$'
    fallback_match = re.search(fallback_pattern, filename)
    
    if fallback_match:
        return fallback_match.group(1)
    
    return ""


def format_kb_reference(kb_path: str, label: str = "") -> str:
    """
    Format knowledge base reference as PubMed URL.
    
    Args:
        kb_path: Knowledge base file path
        label: Optional label for the reference
        
    Returns:
        str: Formatted PubMed URL or original path if PubMed ID not found
    """
    pubmed_id = extract_pubmed_id_from_kb_path(kb_path)
    
    if pubmed_id:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"
    
    # Fallback to original path if PubMed ID not found
    return kb_path


def create_references_section(sources_gathered: List[Dict]) -> str:
    """
    Create a properly formatted References section with improved visual formatting.
    
    Args:
        sources_gathered: List of source dictionaries with 'value', 'short_url', 'label'
        
    Returns:
        str: Formatted references section with numbers first and line breaks
    """
    if not sources_gathered:
        return ""
    
    references = []
    for idx, source in enumerate(sources_gathered, 1):
        value = source.get("value", "")
        label = source.get("label", "")
        short_url = source.get("short_url", "")
        
        # Format reference based on source type
        if short_url.startswith("[KB-"):
            # Knowledge base source - convert to PubMed URL
            pubmed_url = format_kb_reference(value, label)
            reference_text = f"[{idx}] {pubmed_url}"
        else:
            # Web source - use full URL with number first
            reference_text = f"[{idx}] {value}"
        
        references.append(reference_text)
    
    # Join with line breaks for better visualization
    return "\n\n## References\n\n" + "\n\n".join(references)


def resolve_urls(urls_to_resolve: List[Any], id: int) -> Dict[str, str]:
    """
    Create a map of the vertex ai search urls (very long) to a short url with a unique id for each url.
    Ensures each original URL gets a consistent shortened form while maintaining uniqueness.
    """
    prefix = f"https://vertexaisearch.cloud.google.com/id/"
    urls = [site.web.uri for site in urls_to_resolve]

    # Create a dictionary that maps each unique URL to its first occurrence index
    resolved_map = {}
    for idx, url in enumerate(urls):
        if url not in resolved_map:
            resolved_map[url] = f"{prefix}{id}-{idx}"

    return resolved_map


def insert_citation_markers(text, citations_list):
    """
    Inserts citation markers into a text string based on start and end indices.

    Args:
        text (str): The original text string.
        citations_list (list): A list of dictionaries, where each dictionary
                               contains 'start_index', 'end_index', and
                               'segment_string' (the marker to insert).
                               Indices are assumed to be for the original text.

    Returns:
        str: The text with citation markers inserted.
    """
    # Sort citations by end_index in descending order.
    # If end_index is the same, secondary sort by start_index descending.
    # This ensures that insertions at the end of the string don't affect
    # the indices of earlier parts of the string that still need to be processed.
    sorted_citations = sorted(
        citations_list, key=lambda c: (c["end_index"], c["start_index"]), reverse=True
    )

    modified_text = text
    for citation_info in sorted_citations:
        # These indices refer to positions in the *original* text,
        # but since we iterate from the end, they remain valid for insertion
        # relative to the parts of the string already processed.
        end_idx = citation_info["end_index"]
        marker_to_insert = ""
        for segment in citation_info["segments"]:
            marker_to_insert += f" [{segment['label']}]({segment['short_url']})"
        # Insert the citation marker at the original end_idx position
        modified_text = (
            modified_text[:end_idx] + marker_to_insert + modified_text[end_idx:]
        )

    return modified_text


def get_citations(response, resolved_urls_map):
    """
    Extracts and formats citation information from a Gemini model's response.

    This function processes the grounding metadata provided in the response to
    construct a list of citation objects. Each citation object includes the
    start and end indices of the text segment it refers to, and a string
    containing formatted markdown links to the supporting web chunks.

    Args:
        response: The response object from the Gemini model, expected to have
                  a structure including `candidates[0].grounding_metadata`.
                  It also relies on a `resolved_map` being available in its
                  scope to map chunk URIs to resolved URLs.

    Returns:
        list: A list of dictionaries, where each dictionary represents a citation
              and has the following keys:
              - "start_index" (int): The starting character index of the cited
                                     segment in the original text. Defaults to 0
                                     if not specified.
              - "end_index" (int): The character index immediately after the
                                   end of the cited segment (exclusive).
              - "segments" (list[str]): A list of individual markdown-formatted
                                        links for each grounding chunk.
              - "segment_string" (str): A concatenated string of all markdown-
                                        formatted links for the citation.
              Returns an empty list if no valid candidates or grounding supports
              are found, or if essential data is missing.
    """
    citations = []

    # Ensure response and necessary nested structures are present
    if not response or not response.candidates:
        return citations

    candidate = response.candidates[0]
    if (
        not hasattr(candidate, "grounding_metadata")
        or not candidate.grounding_metadata
        or not hasattr(candidate.grounding_metadata, "grounding_supports")
    ):
        return citations

    for support in candidate.grounding_metadata.grounding_supports:
        citation = {}

        # Ensure segment information is present
        if not hasattr(support, "segment") or support.segment is None:
            continue  # Skip this support if segment info is missing

        start_index = (
            support.segment.start_index
            if support.segment.start_index is not None
            else 0
        )

        # Ensure end_index is present to form a valid segment
        if support.segment.end_index is None:
            continue  # Skip if end_index is missing, as it's crucial

        # Add 1 to end_index to make it an exclusive end for slicing/range purposes
        # (assuming the API provides an inclusive end_index)
        citation["start_index"] = start_index
        citation["end_index"] = support.segment.end_index

        citation["segments"] = []
        if (
            hasattr(support, "grounding_chunk_indices")
            and support.grounding_chunk_indices
        ):
            for ind in support.grounding_chunk_indices:
                try:
                    chunk = candidate.grounding_metadata.grounding_chunks[ind]
                    resolved_url = resolved_urls_map.get(chunk.web.uri, None)
                    citation["segments"].append(
                        {
                            "label": chunk.web.title.split(".")[:-1][0],
                            "short_url": resolved_url,
                            "value": chunk.web.uri,
                        }
                    )
                except (IndexError, AttributeError, NameError):
                    # Handle cases where chunk, web, uri, or resolved_map might be problematic
                    # For simplicity, we'll just skip adding this particular segment link
                    # In a production system, you might want to log this.
                    pass
        citations.append(citation)
    return citations


def prepare_content_with_citations(content_segments: List[Dict], sources_gathered: List[Dict]) -> str:
    """
    Prepare content with clear citation markers for LLM processing.
    
    This function takes raw content segments and their associated sources,
    then creates a formatted text that clearly shows which parts of the content
    can be cited with which markers.
    
    Args:
        content_segments: List of content dictionaries with 'content' and 'source_index'
        sources_gathered: List of source dictionaries with 'value', 'short_url', 'label'
        
    Returns:
        str: Formatted content with clear citation opportunities
    """
    if not content_segments or not sources_gathered:
        return ""
    
    formatted_content = ""
    
    for segment in content_segments:
        content = segment.get("content", "")
        source_indices = segment.get("source_indices", [])
        
        if content:
            # Add the content
            formatted_content += content
            
            # Add citation markers if available
            if source_indices:
                citation_markers = []
                for idx in source_indices:
                    if 0 <= idx < len(sources_gathered):
                        source = sources_gathered[idx]
                        marker = source.get("short_url", f"[{idx}]")
                        citation_markers.append(marker)
                
                if citation_markers:
                    formatted_content += " " + "".join(citation_markers)
            
            formatted_content += "\n\n"
    
    return formatted_content


def enhance_research_summaries_with_citations(summaries: List[str], sources_gathered: List[Dict]) -> str:
    """
    Enhance research summaries by ensuring proper citation markers are preserved
    and clearly mapping sources to content.
    
    Args:
        summaries: List of research summary strings
        sources_gathered: List of source dictionaries
        
    Returns:
        str: Enhanced summaries with clear citation guidance
    """
    if not summaries:
        return ""
    
    # Combine all summaries
    combined_summaries = "\n\n---RESEARCH SUMMARY---\n\n".join(summaries)
    
    # Add source mapping at the end
    source_mapping = format_research_citations(sources_gathered)
    
    if source_mapping:
        enhanced_content = combined_summaries + "\n\n" + source_mapping
        
        # Add additional guidance for the LLM
        enhanced_content += """

IMPORTANT CITATION GUIDANCE:
- The above summaries contain citation markers like [0], [1], [KB-1], [KB-2], etc.
- When writing your response, you MUST preserve these exact citation markers
- Each citation marker corresponds to a specific source listed in "Available Sources for Citation"
- Place citations immediately after the relevant claim or fact
- Do not invent new citation numbers - only use existing ones from the summaries
- If you reference information that doesn't have a citation marker in the summaries, try to identify which source it likely came from based on the source descriptions above
"""
        
        return enhanced_content
    
    return combined_summaries


def create_traced_content_segments(content: str, source_mapping: Dict[str, int], sources_gathered: List[Dict]) -> str:
    """
    Create content segments with explicit traceability to original sources.
    
    This function takes content and creates explicit mappings between content segments
    and their original sources, making it easier for LLMs to maintain accurate citations.
    
    Args:
        content: The text content to be processed
        source_mapping: Dictionary mapping content snippets to source indices
        sources_gathered: List of source dictionaries
        
    Returns:
        str: Content with explicit source attribution for each segment
    """
    if not content or not source_mapping or not sources_gathered:
        return content
    
    traced_content = ""
    remaining_content = content
    
    # Sort source mappings by their position in the content
    sorted_mappings = sorted(source_mapping.items(), key=lambda x: content.find(x[0]))
    
    for snippet, source_idx in sorted_mappings:
        if snippet in remaining_content and 0 <= source_idx < len(sources_gathered):
            # Find the position of this snippet
            snippet_start = remaining_content.find(snippet)
            
            # Add content before the snippet
            if snippet_start > 0:
                traced_content += remaining_content[:snippet_start]
            
            # Add the snippet with its source marker
            source = sources_gathered[source_idx]
            source_marker = source.get("short_url", f"[{source_idx}]")
            traced_content += f"{snippet} {source_marker}"
            
            # Update remaining content
            remaining_content = remaining_content[snippet_start + len(snippet):]
    
    # Add any remaining content
    traced_content += remaining_content
    
    return traced_content


def validate_citations_in_content(content: str, sources_gathered: List[Dict]) -> Dict[str, List[str]]:
    """
    Validate that all citations in content are properly mapped to real sources.
    
    Args:
        content: Generated content with citation markers
        sources_gathered: List of available sources
        
    Returns:
        Dict with 'valid_citations', 'invalid_citations', and 'missing_sources'
    """
    import re
    
    # Extract all citation markers from content
    citation_pattern = r'\[(?:KB-\d+|\d+|#\d+)\]'
    found_citations = re.findall(citation_pattern, content)
    
    # Get available citation markers from sources
    available_markers = set()
    for source in sources_gathered:
        marker = source.get("short_url", "")
        if marker:
            available_markers.add(marker)
    
    # Validate citations
    valid_citations = []
    invalid_citations = []
    
    for citation in found_citations:
        if citation in available_markers:
            valid_citations.append(citation)
        else:
            invalid_citations.append(citation)
    
    # Check for sources that weren't cited
    cited_markers = set(found_citations)
    missing_sources = [marker for marker in available_markers if marker not in cited_markers]
    
    return {
        "valid_citations": valid_citations,
        "invalid_citations": invalid_citations,
        "missing_sources": missing_sources,
        "citation_coverage": len(valid_citations) / len(available_markers) if available_markers else 0
    }
