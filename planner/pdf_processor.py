# planner/pdf_processor.py
"""
PDF Processing Module

This module handles:
1. Text extraction from any PDF
2. Intelligent structure detection (chapters, topics, sections)
3. Content organization

Works with ANY academic PDF - not just structured syllabi
"""

import pdfplumber
import re
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Universal PDF processor that can extract content from any academic PDF
    """
    
    def __init__(self, pdf_path):
        """
        Initialize processor with PDF path
        
        Args:
            pdf_path (str): Full path to the PDF file
        """
        self.pdf_path = pdf_path
        self.full_text = ""
        self.pages = []
        self.structure = {
            'topics': [],
            'chapters': [],
            'sections': [],
            'metadata': {}
        }
    
    def process(self):
        """
        Main processing method - extracts text and analyzes structure
        
        Returns:
            dict: Contains extracted text, structure, and metadata
        """
        try:
            # Step 1: Extract text from all pages
            self.extract_text()
            
            # Step 2: Detect structure (chapters, topics, etc.)
            self.detect_structure()
            
            # Step 3: Return organized data
            return {
                'success': True,
                'full_text': self.full_text,
                'structure': self.structure,
                'page_count': len(self.pages),
                'error': None
            }
        
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return {
                'success': False,
                'full_text': '',
                'structure': {},
                'page_count': 0,
                'error': str(e)
            }
    
    def extract_text(self):
        """
        Extract text from all pages of the PDF
        """
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    self.pages.append({
                        'page_number': i + 1,
                        'text': page_text
                    })
                    self.full_text += page_text + "\n\n"
            
            logger.info(f"Extracted text from {len(self.pages)} pages")
        
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            raise
    
    def detect_structure(self):
        """
        Intelligently detect document structure
        
        This method uses multiple heuristics to identify:
        - Chapter headings (usually larger, bold, numbered)
        - Topic headings (subheadings)
        - Sections
        
        It works with various PDF formats by looking for patterns
        """
        if not self.full_text:
            return
        
        # Split into lines for analysis
        lines = self.full_text.split('\n')
        
        # Pattern 1: Numbered chapters/topics (e.g., "1. Introduction", "1.1 Basics")
        self.detect_numbered_headings(lines)
        
        # Pattern 2: All caps headings (e.g., "INTRODUCTION", "CHAPTER 1")
        self.detect_caps_headings(lines)
        
        # Pattern 3: Common keywords (Chapter, Unit, Topic, Lesson, etc.)
        self.detect_keyword_headings(lines)
        
        # Pattern 4: Font size detection (if available)
        self.detect_by_formatting()
        
        # Pattern 5: Table of contents detection
        self.detect_toc()
        
        # If no structure detected, create basic structure
        if not self.structure['topics'] and not self.structure['chapters']:
            self.create_fallback_structure(lines)
    
    def detect_numbered_headings(self, lines):
        """
        Detect headings with numbering like:
        - "1. Introduction"
        - "1.1 Cell Biology"
        - "Chapter 1: Anatomy"
        """
        # Regex patterns for numbered sections
        patterns = [
            r'^(\d+)\.\s+(.+)$',  # 1. Topic Name
            r'^(\d+\.\d+)\s+(.+)$',  # 1.1 Topic Name
            r'^(\d+\.\d+\.\d+)\s+(.+)$',  # 1.1.1 Topic Name
            r'^Chapter\s+(\d+)[:\s]+(.+)$',  # Chapter 1: Name
            r'^Unit\s+(\d+)[:\s]+(.+)$',  # Unit 1: Name
            r'^Lesson\s+(\d+)[:\s]+(.+)$',  # Lesson 1: Name
        ]
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    number = match.group(1)
                    title = match.group(2).strip()
                    
                    # Determine if it's a chapter or topic based on numbering
                    if '.' not in number:
                        # Main chapter (single number)
                        self.structure['chapters'].append({
                            'number': number,
                            'title': title,
                            'type': 'chapter'
                        })
                    else:
                        # Sub-topic (has decimal)
                        self.structure['topics'].append({
                            'number': number,
                            'title': title,
                            'type': 'topic'
                        })
                    break
    
    def detect_caps_headings(self, lines):
        """
        Detect ALL CAPS headings which are often used for chapters
        """
        for line in lines:
            line = line.strip()
            
            # Check if line is all caps, has reasonable length, and not too long
            if (line.isupper() and 
                5 < len(line) < 100 and 
                not line.isdigit() and
                ' ' in line):  # Must have at least one space (not just a word)
                
                self.structure['chapters'].append({
                    'number': None,
                    'title': line.title(),  # Convert to title case
                    'type': 'chapter'
                })
    
    def detect_keyword_headings(self, lines):
        """
        Detect headings containing common academic keywords
        """
        keywords = [
            'chapter', 'unit', 'module', 'lesson', 'section',
            'part', 'topic', 'introduction', 'overview', 'summary'
        ]
        
        for line in lines:
            line_lower = line.strip().lower()
            
            # Check if line starts with a keyword
            for keyword in keywords:
                if line_lower.startswith(keyword) and len(line) < 100:
                    self.structure['chapters'].append({
                        'number': None,
                        'title': line.strip(),
                        'type': 'chapter'
                    })
                    break
    
    def detect_by_formatting(self):
        """
        Use formatting clues from PDF if available
        (Some PDFs preserve font size/style information)
        """
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    # Try to get words with formatting
                    words = page.extract_words(extra_attrs=['size', 'fontname'])
                    
                    if not words:
                        continue
                    
                    # Group words by line and detect large text (likely headings)
                    lines = self._group_words_into_lines(words)
                    
                    for line in lines:
                        avg_size = sum(w.get('size', 0) for w in line) / len(line)
                        text = ' '.join(w['text'] for w in line)
                        
                        # If average font size is large, it's likely a heading
                        if avg_size > 14 and len(text) < 100:
                            self.structure['topics'].append({
                                'number': None,
                                'title': text,
                                'type': 'topic'
                            })
        
        except Exception as e:
            logger.warning(f"Could not extract formatting info: {str(e)}")
    
    def _group_words_into_lines(self, words):
        """Helper method to group words into lines based on y-position"""
        lines = defaultdict(list)
        
        for word in words:
            # Round y-position to group words on same line
            y_pos = round(word.get('top', 0))
            lines[y_pos].append(word)
        
        return list(lines.values())
    
    def detect_toc(self):
        """
        Try to find and parse a Table of Contents
        """
        toc_keywords = ['table of contents', 'contents', 'index']
        toc_section = []
        in_toc = False
        
        lines = self.full_text.split('\n')
        
        for line in lines:
            line_lower = line.strip().lower()
            
            # Check if we're entering TOC
            if any(keyword in line_lower for keyword in toc_keywords):
                in_toc = True
                continue
            
            # If in TOC, collect lines until we hit a page number or end pattern
            if in_toc:
                # Stop if we see something like "Page 1" or "Chapter" (actual content)
                if re.match(r'^(page|chapter)\s+\d+', line_lower):
                    break
                
                # Collect potential TOC entries
                if line.strip() and not line.strip().isdigit():
                    toc_section.append(line.strip())
                
                # Stop after collecting reasonable amount
                if len(toc_section) > 100:
                    break
        
        # Parse TOC entries
        for entry in toc_section:
            # Remove page numbers from end
            clean_entry = re.sub(r'\s*\.+\s*\d+\s*$', '', entry)
            clean_entry = re.sub(r'\s+\d+\s*$', '', clean_entry)
            
            if clean_entry and len(clean_entry) > 3:
                self.structure['topics'].append({
                    'number': None,
                    'title': clean_entry,
                    'type': 'topic',
                    'source': 'toc'
                })
    
    def create_fallback_structure(self, lines):
        """
        Create basic structure if no patterns detected
        
        Splits document into sections based on:
        - Page breaks
        - Paragraph breaks
        - Length thresholds
        """
        current_section = []
        section_count = 1
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                if current_section:
                    # Save current section
                    section_text = ' '.join(current_section)
                    if len(section_text) > 100:  # Minimum length
                        self.structure['topics'].append({
                            'number': str(section_count),
                            'title': f"Section {section_count}",
                            'type': 'topic',
                            'content_preview': section_text[:200] + "..."
                        })
                        section_count += 1
                        current_section = []
                continue
            
            current_section.append(line)
            
            # Split into sections every ~500 words
            if len(current_section) > 50:
                section_text = ' '.join(current_section)
                if len(section_text.split()) > 500:
                    self.structure['topics'].append({
                        'number': str(section_count),
                        'title': f"Section {section_count}",
                        'type': 'topic',
                        'content_preview': section_text[:200] + "..."
                    })
                    section_count += 1
                    current_section = []
        
        # Add remaining content
        if current_section:
            section_text = ' '.join(current_section)
            if len(section_text) > 100:
                self.structure['topics'].append({
                    'number': str(section_count),
                    'title': f"Section {section_count}",
                    'type': 'topic',
                    'content_preview': section_text[:200] + "..."
                })


def process_pdf(pdf_path):
    """
    Convenience function to process a PDF
    
    Args:
        pdf_path (str): Path to PDF file
    
    Returns:
        dict: Processing results
    """
    processor = PDFProcessor(pdf_path)
    return processor.process()


def extract_topics_from_structure(structure):
    """
    Convert detected structure into a clean list of topics
    
    Args:
        structure (dict): Structure returned by PDFProcessor
    
    Returns:
        list: List of topic dictionaries
    """
    topics = []
    
    # Combine chapters and topics, removing duplicates
    all_items = structure.get('chapters', []) + structure.get('topics', [])
    
    seen_titles = set()
    
    for item in all_items:
        title = item.get('title', '').strip()
        
        # Skip if empty or duplicate
        if not title or title in seen_titles:
            continue
        
        seen_titles.add(title)
        
        topics.append({
            'name': title,
            'number': item.get('number'),
            'type': item.get('type', 'topic'),
            'content_preview': item.get('content_preview', '')
        })
    
    return topics