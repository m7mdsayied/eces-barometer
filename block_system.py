"""
Block-based editing system for ECES Barometer
Defines block types, templates, LaTeX generation, and parsing
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ============================================
# ENUMS: Block Types and Section Types
# ============================================

class BlockType(Enum):
    """Available block types"""
    # Core blocks (available everywhere)
    PARAGRAPH = "paragraph"
    TITLE = "title"
    CHART = "chart"
    BULLET_LIST = "bullet_list"
    TEXT_CHART_ROW = "text_chart_row"
    SPACER = "spacer"

    # Section-specific blocks
    HIGHLIGHT_BOX = "highlight_box"  # Executive Summary only
    SUBHEADER_LEGEND = "subheader_legend"  # Executive Summary only
    PAGE_SETUP = "page_setup"  # Section starts


class SectionType(Enum):
    """Section types with specific styling"""
    EXECUTIVE_SUMMARY = "executive_summary"
    MACRO_OVERVIEW = "macro_overview"
    ANALYSIS_OVERALL = "analysis_overall"
    CONSTRAINTS = "constraints"
    SUBINDICES = "subindices"
    TABLES = "tables"


# ============================================
# BLOCK DATA STRUCTURE
# ============================================

@dataclass
class Block:
    """Base block structure"""
    type: BlockType
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    estimated_height: int = 50  # pixels

    def to_latex(self) -> str:
        """Convert block to LaTeX code"""
        generator = BLOCK_GENERATORS.get(self.type)
        if not generator:
            raise ValueError(f"No generator for block type: {self.type}")
        return generator(self)

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata,
            "estimated_height": self.estimated_height
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Block':
        """Deserialize from dictionary"""
        return cls(
            type=BlockType(data["type"]),
            content=data["content"],
            metadata=data.get("metadata", {}),
            estimated_height=data.get("estimated_height", 50)
        )


# ============================================
# LATEX GENERATORS (Block -> LaTeX)
# ============================================

def generate_paragraph(block: Block) -> str:
    """Generate LaTeX for paragraph block"""
    font_size = block.metadata.get("font_size", 10)
    line_height = block.metadata.get("line_height", 13)
    bold = block.metadata.get("bold", False)
    color = block.metadata.get("color", "black")

    # Build LaTeX
    latex = "\\noindent\n"
    latex += f"{{\\fontsize{{{font_size}}}{{{line_height}}}\\selectfont"

    if color and color != "black":
        latex += f" \\color{{{color}}}"

    if bold:
        latex += " \\textbf{"

    latex += f"\n{block.content}"

    if bold:
        latex += "}"

    latex += "\n}\n\\vspace{0.5em}\n"

    return latex


def generate_title(block: Block) -> str:
    """Generate LaTeX for title block"""
    level = block.metadata.get("level", 1)
    color = block.metadata.get("color", "ecestitle")
    underline = block.metadata.get("underline", False)

    # Font sizes by level
    sizes = {1: (22, 26), 2: (14, 18), 3: (11, 14)}
    font_size, line_height = sizes.get(level, (10, 13))

    latex = "\\noindent\n"
    latex += f"{{\\fontsize{{{font_size}}}{{{line_height}}}\\selectfont \\textbf{{\\color{{{color}}}"

    if underline:
        latex += " \\underline{"

    latex += f"\n{block.content}"

    if underline:
        latex += "}"

    latex += "\n}}} \\vspace{0.5em}\n"

    return latex


def generate_chart(block: Block) -> str:
    """Generate LaTeX for chart block"""
    image_file = block.content  # Image filename
    width = block.metadata.get("width", "linewidth")
    alignment = block.metadata.get("alignment", "center")

    latex = "\\noindent\n"

    if alignment == "center":
        latex += "\\begin{center}\n"

    # Handle width format
    if width == "linewidth":
        latex += f"    \\includegraphics[width=\\linewidth]{{{image_file}}}\n"
    else:
        latex += f"    \\includegraphics[width={width}]{{{image_file}}}\n"

    if alignment == "center":
        latex += "\\end{center}\n"

    latex += "\\vspace{0.5em}\n"

    return latex


def generate_bullet_list(block: Block) -> str:
    """Generate LaTeX for bullet list block"""
    items = block.content  # List of strings

    latex = "\\begin{itemize}\n"

    for item in items:
        latex += f"    \\item {item}\n"

    latex += "\\end{itemize}\n"
    latex += "\\vspace{0.5em}\n"

    return latex


def generate_text_chart_row(block: Block) -> str:
    """Generate LaTeX for text-chart row block (side by side)"""
    text = block.content.get("text", "")
    chart_file = block.content.get("chart_file", "")
    text_width = block.metadata.get("text_width", 0.55)
    chart_width = block.metadata.get("chart_width", 0.42)
    font_size = block.metadata.get("font_size", 10)
    line_height = block.metadata.get("line_height", 13)

    latex = "\\noindent\n"
    latex += f"\\begin{{minipage}}[t]{{{text_width}\\textwidth}}\n"
    latex += f"    \\fontsize{{{font_size}}}{{{line_height}}}\\selectfont\n"
    latex += f"    {text}\n"
    latex += "\\end{minipage}%\n"
    latex += "\\hfill\n"
    latex += f"\\begin{{minipage}}[t]{{{chart_width}\\textwidth}}\n"
    latex += "    \\vspace{0pt}\n"
    latex += "    \\centering\n"
    latex += f"    \\includegraphics[width=\\linewidth]{{{chart_file}}}\n"
    latex += "\\end{minipage}\n"
    latex += "\\vspace{1em}\n"

    return latex


def generate_spacer(block: Block) -> str:
    """Generate LaTeX for spacer block"""
    size = block.metadata.get("size", "1em")
    return f"\\vspace{{{size}}}\n"


def generate_highlight_box(block: Block) -> str:
    """Generate LaTeX for highlight box block (Executive Summary)"""
    sections = block.content  # List of {title, color, content}

    latex = "\\noindent\n"
    latex += "\\begin{tikzpicture}\n"
    latex += "    \\node[draw=black, line width=0.8pt, inner sep=10pt, align=justify, text width=14.8cm] (box) {\n"
    latex += "        \\fontsize{10}{13}\\selectfont\n\n"

    for i, section in enumerate(sections):
        title = section.get("title", "")
        color = section.get("color", "black")
        content = section.get("content", "")

        if title:
            latex += f"        \\textbf{{\\color{{{color}}} \\underline{{{title}}}}} \\\\\n"

        latex += f"        \\color{{{color}}}\n"
        latex += f"        {content}\n"

        if i < len(sections) - 1:
            latex += "\n        \\vspace{0.3em}\n"

    latex += "    };\n"
    latex += "\\end{tikzpicture}\n"
    latex += "\\vspace{1em}\n"

    return latex


def generate_subheader_legend(block: Block) -> str:
    """Generate LaTeX for subheader with legend block"""
    text = block.content.get("text", "")
    legend_image = block.content.get("legend_image", "arrow.png")

    # Split multiline text
    text_lines = text.split("\n")

    latex = "\\noindent\n"
    latex += "\\begin{minipage}[t]{0.50\\textwidth}\n"
    latex += "    \\vspace{0pt}\n"

    for line in text_lines:
        if line.strip():
            latex += f"    \\textbf{{\\underline{{{line.strip()}}}}} \\\\\n"

    latex += "\\end{minipage}%\n"
    latex += "\\hfill\n"
    latex += "\\begin{minipage}[t]{0.45\\textwidth}\n"
    latex += "    \\vspace{0pt}\n"
    latex += "    \\centering\n"
    latex += f"    \\includegraphics[width=\\linewidth, height=1cm]{{{legend_image}}}\n"
    latex += "\\end{minipage}\n"
    latex += "\\vspace{1em}\n"

    return latex


def generate_page_setup(block: Block) -> str:
    """Generate LaTeX for page setup block"""
    background = block.content.get("background", "con_bg.png")
    geometry = block.content.get("geometry", {
        "left": "2cm",
        "right": "1.5cm",
        "top": "3cm",
        "bottom": "2.5cm"
    })
    page_number = block.content.get("page_number", 1)

    latex = f"\\newgeometry{{left={geometry.get('left', '2cm')}, right={geometry.get('right', '1.5cm')}, "
    latex += f"top={geometry.get('top', '3cm')}, bottom={geometry.get('bottom', '2.5cm')}}}\n\n"

    latex += "\\begin{tikzpicture}[remember picture, overlay]\n"
    latex += "    \\node[anchor=north west, inner sep=0pt] at (current page.north west) {\n"
    latex += f"        \\includegraphics[width=\\paperwidth, height=\\paperheight]{{{background}}}\n"
    latex += "    };\n"
    latex += "    \\node[anchor=south east] at ([xshift=-1cm, yshift=1cm]current page.south east) {\n"
    latex += f"        \\fontsize{{14}}{{14}}\\selectfont \\textbf{{{page_number}}}\n"
    latex += "    };\n"
    latex += "\\end{tikzpicture}\n\n"

    return latex


# Block generator registry
BLOCK_GENERATORS = {
    BlockType.PARAGRAPH: generate_paragraph,
    BlockType.TITLE: generate_title,
    BlockType.CHART: generate_chart,
    BlockType.BULLET_LIST: generate_bullet_list,
    BlockType.TEXT_CHART_ROW: generate_text_chart_row,
    BlockType.SPACER: generate_spacer,
    BlockType.HIGHLIGHT_BOX: generate_highlight_box,
    BlockType.SUBHEADER_LEGEND: generate_subheader_legend,
    BlockType.PAGE_SETUP: generate_page_setup,
}


# ============================================
# SECTION BLOCK PALETTES
# ============================================

SECTION_PALETTES = {
    SectionType.EXECUTIVE_SUMMARY: [
        BlockType.PAGE_SETUP,
        BlockType.TITLE,
        BlockType.PARAGRAPH,
        BlockType.SUBHEADER_LEGEND,
        BlockType.HIGHLIGHT_BOX,
        BlockType.TEXT_CHART_ROW,
        BlockType.CHART,
        BlockType.BULLET_LIST,
        BlockType.SPACER,
    ],
    SectionType.MACRO_OVERVIEW: [
        BlockType.PAGE_SETUP,
        BlockType.TITLE,
        BlockType.PARAGRAPH,
        BlockType.CHART,
        BlockType.TEXT_CHART_ROW,
        BlockType.BULLET_LIST,
        BlockType.SPACER,
    ],
    SectionType.ANALYSIS_OVERALL: [
        BlockType.PAGE_SETUP,
        BlockType.TITLE,
        BlockType.PARAGRAPH,
        BlockType.CHART,
        BlockType.TEXT_CHART_ROW,
        BlockType.BULLET_LIST,
        BlockType.SPACER,
    ],
    SectionType.CONSTRAINTS: [
        BlockType.PAGE_SETUP,
        BlockType.TITLE,
        BlockType.PARAGRAPH,
        BlockType.CHART,
        BlockType.TEXT_CHART_ROW,
        BlockType.BULLET_LIST,
        BlockType.SPACER,
    ],
    SectionType.SUBINDICES: [
        BlockType.PAGE_SETUP,
        BlockType.TITLE,
        BlockType.PARAGRAPH,
        BlockType.CHART,
        BlockType.TEXT_CHART_ROW,
        BlockType.BULLET_LIST,
        BlockType.SPACER,
    ],
    SectionType.TABLES: [
        BlockType.PAGE_SETUP,
        BlockType.TITLE,
        BlockType.PARAGRAPH,
        BlockType.CHART,
        BlockType.SPACER,
    ],
}


# ============================================
# HEIGHT ESTIMATION
# ============================================

def estimate_block_height(block: Block) -> int:
    """Estimate block height in pixels for pagination"""

    if block.type == BlockType.PARAGRAPH:
        # ~15px per line, estimate lines from character count
        chars = len(str(block.content))
        chars_per_line = 100  # approximate
        lines = max(1, chars // chars_per_line)
        return lines * 15 + 10  # 10px padding

    elif block.type == BlockType.TITLE:
        level = block.metadata.get("level", 1)
        heights = {1: 45, 2: 35, 3: 25}
        return heights.get(level, 25)

    elif block.type == BlockType.CHART:
        # Default chart height, can be overridden
        return block.metadata.get("height", 200)

    elif block.type == BlockType.BULLET_LIST:
        items = block.content if isinstance(block.content, list) else []
        return len(items) * 22 + 15

    elif block.type == BlockType.TEXT_CHART_ROW:
        # Use the larger of text or chart height
        text = block.content.get("text", "") if isinstance(block.content, dict) else ""
        text_height = len(text) // 80 * 15 + 20
        chart_height = 180
        return max(text_height, chart_height)

    elif block.type == BlockType.HIGHLIGHT_BOX:
        # Estimate based on sections
        sections = block.content if isinstance(block.content, list) else []
        total = 30  # padding
        for section in sections:
            content = section.get("content", "") if isinstance(section, dict) else ""
            total += len(content) // 80 * 15 + 30  # title + content
        return total

    elif block.type == BlockType.SUBHEADER_LEGEND:
        return 60

    elif block.type == BlockType.PAGE_SETUP:
        return 0  # Doesn't consume content space

    elif block.type == BlockType.SPACER:
        return 20

    return 50  # default


def calculate_page_breaks(blocks: List[Block], page_height: int = 750) -> List[int]:
    """
    Calculate page break positions
    Returns list of block indices where pages should break
    """
    page_breaks = []
    current_height = 0

    for i, block in enumerate(blocks):
        block_height = estimate_block_height(block)

        # Check if block fits on current page
        if current_height + block_height > page_height and current_height > 0:
            # Start new page
            page_breaks.append(i)
            current_height = block_height
        else:
            current_height += block_height

    return page_breaks


# ============================================
# BLOCK MANAGER
# ============================================

class BlockManager:
    """Manages block operations for a section"""

    def __init__(self, section_type: SectionType):
        self.section_type = section_type
        self.blocks: List[Block] = []
        self.available_blocks = SECTION_PALETTES.get(section_type, list(BlockType))

    def add_block(self, block_type: BlockType, content: Any,
                  metadata: Dict = None, position: int = None) -> Block:
        """Add a new block"""
        if block_type not in self.available_blocks:
            raise ValueError(f"Block type {block_type} not available in {self.section_type}")

        block = Block(
            type=block_type,
            content=content,
            metadata=metadata or {},
        )
        block.estimated_height = estimate_block_height(block)

        if position is None:
            self.blocks.append(block)
        else:
            self.blocks.insert(position, block)

        return block

    def remove_block(self, index: int) -> Optional[Block]:
        """Remove a block by index"""
        if 0 <= index < len(self.blocks):
            return self.blocks.pop(index)
        return None

    def move_block(self, from_index: int, to_index: int) -> bool:
        """Move a block from one position to another"""
        if 0 <= from_index < len(self.blocks) and 0 <= to_index <= len(self.blocks):
            block = self.blocks.pop(from_index)
            # Adjust to_index if needed after removal
            if to_index > from_index:
                to_index -= 1
            self.blocks.insert(to_index, block)
            return True
        return False

    def update_block(self, index: int, content: Any = None, metadata: Dict = None) -> bool:
        """Update a block's content or metadata"""
        if 0 <= index < len(self.blocks):
            if content is not None:
                self.blocks[index].content = content
            if metadata is not None:
                self.blocks[index].metadata.update(metadata)
            # Recalculate height
            self.blocks[index].estimated_height = estimate_block_height(self.blocks[index])
            return True
        return False

    def generate_latex(self) -> str:
        """Generate complete LaTeX for all blocks"""
        latex_parts = []

        for block in self.blocks:
            try:
                latex_parts.append(block.to_latex())
            except Exception as e:
                # Add error comment in LaTeX
                latex_parts.append(f"% ERROR generating block {block.type}: {str(e)}\n")

        return "\n".join(latex_parts)

    def get_page_breaks(self) -> List[int]:
        """Get page break positions"""
        return calculate_page_breaks(self.blocks)

    def get_total_height(self) -> int:
        """Get total estimated height of all blocks"""
        return sum(estimate_block_height(block) for block in self.blocks)

    def export_json(self) -> List[Dict]:
        """Export blocks as JSON-serializable list"""
        return [block.to_dict() for block in self.blocks]

    def import_json(self, data: List[Dict]) -> None:
        """Import blocks from JSON list"""
        self.blocks = [Block.from_dict(block_data) for block_data in data]

    def clear(self) -> None:
        """Clear all blocks"""
        self.blocks = []


# ============================================
# DEFAULT BLOCK TEMPLATES
# ============================================

def get_default_block_content(block_type: BlockType) -> Tuple[Any, Dict]:
    """Get default content and metadata for a new block"""

    defaults = {
        BlockType.PARAGRAPH: (
            "Enter your paragraph text here...",
            {"font_size": 10, "line_height": 13, "bold": False, "color": "black"}
        ),
        BlockType.TITLE: (
            "New Section Title",
            {"level": 2, "color": "ecestitle", "underline": False}
        ),
        BlockType.CHART: (
            "ch1.png",
            {"width": "linewidth", "alignment": "center"}
        ),
        BlockType.BULLET_LIST: (
            ["First point", "Second point", "Third point"],
            {}
        ),
        BlockType.TEXT_CHART_ROW: (
            {"text": "Enter text content here...", "chart_file": "ch1.png"},
            {"text_width": 0.55, "chart_width": 0.42, "font_size": 10, "line_height": 13}
        ),
        BlockType.SPACER: (
            None,
            {"size": "1em"}
        ),
        BlockType.HIGHLIGHT_BOX: (
            [
                {"title": "Section Title:", "color": "textblue", "content": "-- Content here..."}
            ],
            {}
        ),
        BlockType.SUBHEADER_LEGEND: (
            {"text": "Subheader text\nSecond line", "legend_image": "arrow.png"},
            {}
        ),
        BlockType.PAGE_SETUP: (
            {
                "background": "con_bg.png",
                "geometry": {"left": "2cm", "right": "1.5cm", "top": "3cm", "bottom": "2.5cm"},
                "page_number": 1
            },
            {}
        ),
    }

    return defaults.get(block_type, ("", {}))


# ============================================
# BLOCK DISPLAY NAMES AND ICONS
# ============================================

BLOCK_DISPLAY_INFO = {
    BlockType.PARAGRAPH: {"name": "Paragraph", "icon": "📄", "description": "Text paragraph"},
    BlockType.TITLE: {"name": "Title", "icon": "📌", "description": "Section heading"},
    BlockType.CHART: {"name": "Chart", "icon": "📊", "description": "Chart/image"},
    BlockType.BULLET_LIST: {"name": "Bullet List", "icon": "📋", "description": "Bulleted list"},
    BlockType.TEXT_CHART_ROW: {"name": "Text + Chart", "icon": "📊", "description": "Side-by-side layout"},
    BlockType.SPACER: {"name": "Spacer", "icon": "↕️", "description": "Vertical space"},
    BlockType.HIGHLIGHT_BOX: {"name": "Highlight Box", "icon": "📦", "description": "Bordered highlight box"},
    BlockType.SUBHEADER_LEGEND: {"name": "Subheader + Legend", "icon": "🏷️", "description": "Subheader with legend image"},
    BlockType.PAGE_SETUP: {"name": "Page Setup", "icon": "⚙️", "description": "Page background and margins"},
}


def get_block_icon(block_type: BlockType) -> str:
    """Get icon for block type"""
    return BLOCK_DISPLAY_INFO.get(block_type, {}).get("icon", "▪️")


def get_block_name(block_type: BlockType) -> str:
    """Get display name for block type"""
    return BLOCK_DISPLAY_INFO.get(block_type, {}).get("name", block_type.value)


# ============================================
# LATEX PARSER (LaTeX -> Blocks)
# ============================================

class LaTeXParser:
    """Parse LaTeX content into blocks"""

    def __init__(self, section_type: SectionType = None):
        self.section_type = section_type

    def parse(self, latex_content: str) -> List[Block]:
        """
        Parse LaTeX content into blocks

        Strategy:
        1. First try marker-based parsing (% BLOCK:TYPE)
        2. Fall back to regex patterns for unmarked content
        """
        # Try marker-based parsing first
        blocks = self._parse_by_markers(latex_content)

        if blocks:
            return blocks

        # Fall back to regex-based parsing
        return self._parse_by_regex(latex_content)

    def _parse_metadata_string(self, meta_str: str) -> Dict[str, Any]:
        """Parse metadata from marker string like 'key1=value1 key2=value2'"""
        metadata = {}
        if not meta_str:
            return metadata

        # Parse key=value pairs
        for part in meta_str.strip().split():
            if '=' in part:
                key, val = part.split('=', 1)
                # Try to convert to appropriate type
                if val.lower() == 'true':
                    metadata[key] = True
                elif val.lower() == 'false':
                    metadata[key] = False
                elif val.isdigit():
                    metadata[key] = int(val)
                else:
                    metadata[key] = val
        return metadata

    def _parse_by_markers(self, latex_content: str) -> List[Block]:
        """Parse content using % BLOCK:TYPE markers"""
        blocks = []

        # Find all block markers
        marker_pattern = r'%\s*BLOCK:(\w+)(?:\s+(.+?))?$'
        lines = latex_content.split('\n')

        current_block_type = None
        current_metadata = {}
        current_content_lines = []
        current_position = 0

        for i, line in enumerate(lines):
            match = re.match(marker_pattern, line.strip())

            if match:
                # Save previous block if exists
                if current_block_type and current_content_lines:
                    block = self._create_block_from_marker(
                        current_block_type,
                        '\n'.join(current_content_lines),
                        current_metadata,
                        current_position
                    )
                    if block:
                        blocks.append(block)

                # Start new block
                current_block_type = match.group(1)
                current_metadata = self._parse_metadata_string(match.group(2))
                current_content_lines = []
                current_position = i

            elif current_block_type:
                # Skip certain markers
                if line.strip().startswith('% BLOCK:END'):
                    if current_content_lines:
                        block = self._create_block_from_marker(
                            current_block_type,
                            '\n'.join(current_content_lines),
                            current_metadata,
                            current_position
                        )
                        if block:
                            blocks.append(block)
                    current_block_type = None
                    current_content_lines = []
                elif not line.strip().startswith('% ========='):
                    current_content_lines.append(line)

        # Save last block
        if current_block_type and current_content_lines:
            block = self._create_block_from_marker(
                current_block_type,
                '\n'.join(current_content_lines),
                current_metadata,
                current_position
            )
            if block:
                blocks.append(block)

        return blocks

    def _create_block_from_marker(self, block_type_str: str, content: str,
                                   metadata: Dict, position: int) -> Optional[Block]:
        """Create a Block from marker info"""
        # Map marker type to BlockType
        type_map = {
            'PAGE_SETUP': BlockType.PAGE_SETUP,
            'TITLE': BlockType.TITLE,
            'PARAGRAPH': BlockType.PARAGRAPH,
            'CHART': BlockType.CHART,
            'BULLET_LIST': BlockType.BULLET_LIST,
            'TEXT_CHART_ROW': BlockType.TEXT_CHART_ROW,
            'HIGHLIGHT_BOX': BlockType.HIGHLIGHT_BOX,
            'SUBHEADER_LEGEND': BlockType.SUBHEADER_LEGEND,
            'SPACER': BlockType.SPACER,
        }

        block_type = type_map.get(block_type_str)
        if not block_type:
            return None

        # Clean content
        content = content.strip()
        if not content:
            return None

        # Extract block-specific content based on type
        if block_type == BlockType.PAGE_SETUP:
            # Extract background and page number from content
            bg_match = re.search(r'\\includegraphics\[.*?\]\{([^}]+)\}', content)
            background = metadata.get('background', bg_match.group(1) if bg_match else 'con_bg.png')

            page_match = re.search(r'\\textbf\{(\d+)\}', content)
            page_number = metadata.get('page', int(page_match.group(1)) if page_match else 1)

            # Extract geometry
            geom_match = re.search(r'\\newgeometry\{([^}]+)\}', content)
            geometry = {"left": "5cm", "right": "1.5cm", "top": "3cm", "bottom": "2.5cm"}
            if geom_match:
                for param in geom_match.group(1).split(','):
                    if '=' in param:
                        key, val = param.strip().split('=')
                        geometry[key.strip()] = val.strip()

            block_content = {
                "background": background,
                "geometry": geometry,
                "page_number": page_number
            }

        elif block_type == BlockType.TITLE:
            # Extract title text
            title_match = re.search(r'\\textbf\{\\color\{\w+\}[^}]*\}?\s*([^}]+)\}', content, re.DOTALL)
            if title_match:
                block_content = title_match.group(1).strip()
            else:
                # Try simpler pattern
                text_match = re.search(r'\n([^\n\\]+)\n', content)
                block_content = text_match.group(1).strip() if text_match else content

            # Clean up
            block_content = re.sub(r'\\underline\{([^}]+)\}', r'\1', block_content)
            block_content = block_content.strip()

        elif block_type == BlockType.PARAGRAPH:
            # Extract text content, removing LaTeX formatting
            text = content
            text = re.sub(r'\\noindent\s*', '', text)
            text = re.sub(r'\{\\fontsize\{\d+\}\{\d+\}\\selectfont\s*', '', text)
            text = re.sub(r'\\color\{\w+\}\s*', '', text)
            text = re.sub(r'\}\s*\\vspace\{[^}]+\}', '', text)
            text = re.sub(r'^\s*\{', '', text)
            text = re.sub(r'\}\s*$', '', text)
            block_content = text.strip()

        elif block_type == BlockType.CHART:
            # Extract image filename
            img_match = re.search(r'\\includegraphics\[[^\]]*\]\{([^}]+)\}', content)
            block_content = metadata.get('file', img_match.group(1) if img_match else 'ch1.png')

        elif block_type == BlockType.BULLET_LIST:
            # Extract list items
            items = re.findall(r'\\item\s*(.*?)(?=\\item|\\end\{itemize\}|$)', content, re.DOTALL)
            block_content = [item.strip() for item in items if item.strip()]

        elif block_type == BlockType.TEXT_CHART_ROW:
            # Extract text and chart
            text_match = re.search(r'\\begin\{minipage\}.*?\\fontsize\{\d+\}\{\d+\}\\selectfont\s*(.*?)\\end\{minipage\}', content, re.DOTALL)
            chart_match = re.search(r'\\includegraphics\[[^\]]*\]\{([^}]+)\}', content)

            text = text_match.group(1).strip() if text_match else ""
            chart = metadata.get('chart', chart_match.group(1) if chart_match else 'ch1.png')

            block_content = {"text": text, "chart_file": chart}

        elif block_type == BlockType.HIGHLIGHT_BOX:
            # Parse sections within highlight box
            sections = []
            section_pattern = r'\\textbf\{\\color\{(\w+)\}\s*\\underline\{([^}]+)\}\}\s*\\\\?\s*\\color\{\1\}\s*(.*?)(?=\\textbf\{\\color|\\vspace|$)'

            for smatch in re.finditer(section_pattern, content, re.DOTALL):
                sections.append({
                    "title": smatch.group(2).strip(),
                    "color": smatch.group(1),
                    "content": smatch.group(3).strip()
                })

            if not sections:
                # No colored sections, treat as single block
                sections = [{"title": "", "color": "black", "content": content}]

            block_content = sections

        elif block_type == BlockType.SUBHEADER_LEGEND:
            # Extract text and legend image
            underlines = re.findall(r'\\textbf\{\\underline\{([^}]+)\}\}', content)
            text = '\n'.join(underlines) if underlines else ""

            img_match = re.search(r'\\includegraphics\[[^\]]*\]\{([^}]+)\}', content)
            legend = metadata.get('legend', img_match.group(1) if img_match else 'arrow.png')

            block_content = {"text": text, "legend_image": legend}

        else:
            block_content = content

        block = Block(
            type=block_type,
            content=block_content,
            metadata=metadata
        )
        block.estimated_height = estimate_block_height(block)

        return block

    def _parse_by_regex(self, latex_content: str) -> List[Block]:
        """Fall back to regex-based parsing for unmarked content"""
        blocks = []

        # Remove comments (but preserve % in content)
        lines = latex_content.split('\n')
        cleaned_lines = []
        for line in lines:
            # Keep lines that are pure comments for structure understanding
            if line.strip().startswith('%'):
                continue  # Skip pure comment lines
            # Remove inline comments
            if '%' in line and not line.strip().startswith('%'):
                # Find % not preceded by \
                idx = 0
                while idx < len(line):
                    if line[idx] == '%' and (idx == 0 or line[idx-1] != '\\'):
                        line = line[:idx]
                        break
                    idx += 1
            cleaned_lines.append(line)

        content = '\n'.join(cleaned_lines)

        # Parse page setup blocks
        content = self._extract_page_setups(content, blocks)

        # Parse highlight boxes (tikzpicture with node[draw=black])
        content = self._extract_highlight_boxes(content, blocks)

        # Parse subheader legend blocks
        content = self._extract_subheader_legends(content, blocks)

        # Parse text-chart rows (minipage pairs)
        content = self._extract_text_chart_rows(content, blocks)

        # Parse standalone charts
        content = self._extract_charts(content, blocks)

        # Parse bullet lists
        content = self._extract_bullet_lists(content, blocks)

        # Parse titles
        content = self._extract_titles(content, blocks)

        # Parse paragraphs (remaining fontsize blocks)
        content = self._extract_paragraphs(content, blocks)

        # Sort blocks by their original position
        blocks.sort(key=lambda b: b.metadata.get('_position', 9999))

        # Remove position metadata
        for block in blocks:
            block.metadata.pop('_position', None)

        return blocks

    def _extract_page_setups(self, content: str, blocks: List[Block]) -> str:
        """Extract page setup blocks"""
        # Pattern for newgeometry followed by tikzpicture with background
        pattern = r'\\newgeometry\{([^}]+)\}\s*\\begin\{tikzpicture\}\[remember picture,\s*overlay\](.*?)\\end\{tikzpicture\}'

        for match in re.finditer(pattern, content, re.DOTALL):
            position = match.start()
            geometry_str = match.group(1)
            tikz_content = match.group(2)

            # Parse geometry
            geometry = {}
            for param in geometry_str.split(','):
                if '=' in param:
                    key, val = param.strip().split('=')
                    geometry[key.strip()] = val.strip()

            # Extract background image
            bg_match = re.search(r'\\includegraphics\[.*?\]\{([^}]+)\}', tikz_content)
            background = bg_match.group(1) if bg_match else "con_bg.png"

            # Extract page number
            page_match = re.search(r'\\textbf\{(\d+)\}', tikz_content)
            page_number = int(page_match.group(1)) if page_match else 1

            block = Block(
                type=BlockType.PAGE_SETUP,
                content={
                    "background": background,
                    "geometry": geometry,
                    "page_number": page_number
                },
                metadata={"_position": position},
                estimated_height=0
            )
            blocks.append(block)

        # Remove matched content
        content = re.sub(pattern, '', content, flags=re.DOTALL)

        # Also handle standalone tikzpicture backgrounds (without newgeometry)
        standalone_pattern = r'\\begin\{tikzpicture\}\[remember picture,\s*overlay\](.*?)\\end\{tikzpicture\}'
        for match in re.finditer(standalone_pattern, content, re.DOTALL):
            tikz_content = match.group(1)
            if 'includegraphics' in tikz_content and 'paperwidth' in tikz_content:
                position = match.start()

                bg_match = re.search(r'\\includegraphics\[.*?\]\{([^}]+)\}', tikz_content)
                background = bg_match.group(1) if bg_match else "con_bg.png"

                page_match = re.search(r'\\textbf\{(\d+)\}', tikz_content)
                page_number = int(page_match.group(1)) if page_match else 1

                block = Block(
                    type=BlockType.PAGE_SETUP,
                    content={
                        "background": background,
                        "geometry": {"left": "5cm", "right": "1.5cm", "top": "3cm", "bottom": "2.5cm"},
                        "page_number": page_number
                    },
                    metadata={"_position": position},
                    estimated_height=0
                )
                blocks.append(block)

        content = re.sub(standalone_pattern, '', content, flags=re.DOTALL)

        return content

    def _extract_highlight_boxes(self, content: str, blocks: List[Block]) -> str:
        """Extract highlight box blocks (tikzpicture with bordered node)"""
        pattern = r'\\begin\{tikzpicture\}\s*\\node\[draw=black[^\]]*\]\s*\(box\)\s*\{(.*?)\};\s*\\end\{tikzpicture\}'

        for match in re.finditer(pattern, content, re.DOTALL):
            position = match.start()
            inner_content = match.group(1)

            # Parse sections within the box
            sections = []

            # Look for colored sections with titles
            section_pattern = r'\\textbf\{\\color\{(\w+)\}\s*\\underline\{([^}]+)\}\}\s*\\\\?\s*\\color\{\1\}(.*?)(?=\\textbf\{\\color|\\vspace|$)'
            section_matches = list(re.finditer(section_pattern, inner_content, re.DOTALL))

            if section_matches:
                for smatch in section_matches:
                    sections.append({
                        "title": smatch.group(2).strip(),
                        "color": smatch.group(1),
                        "content": smatch.group(3).strip()
                    })
            else:
                # No colored sections, treat entire content as one section
                clean_content = re.sub(r'\\fontsize\{\d+\}\{\d+\}\\selectfont', '', inner_content)
                clean_content = clean_content.strip()
                if clean_content:
                    sections.append({
                        "title": "",
                        "color": "black",
                        "content": clean_content
                    })

            if sections:
                block = Block(
                    type=BlockType.HIGHLIGHT_BOX,
                    content=sections,
                    metadata={"_position": position}
                )
                block.estimated_height = estimate_block_height(block)
                blocks.append(block)

        content = re.sub(pattern, '', content, flags=re.DOTALL)
        return content

    def _extract_subheader_legends(self, content: str, blocks: List[Block]) -> str:
        """Extract subheader with legend blocks"""
        # Pattern for two minipages where first has underlined text and second has small image
        pattern = r'\\begin\{minipage\}\[t\]\{0\.50?\\textwidth\}(.*?)\\end\{minipage\}%?\s*\\hfill\s*\\begin\{minipage\}\[t\]\{0\.45?\\textwidth\}(.*?)\\includegraphics\[.*?height=1cm\]\{([^}]+)\}(.*?)\\end\{minipage\}'

        for match in re.finditer(pattern, content, re.DOTALL):
            position = match.start()
            text_content = match.group(1)
            legend_image = match.group(3)

            # Extract underlined text
            underline_matches = re.findall(r'\\textbf\{\\underline\{([^}]+)\}\}', text_content)
            if underline_matches:
                text = '\n'.join([t.strip() for t in underline_matches])

                block = Block(
                    type=BlockType.SUBHEADER_LEGEND,
                    content={"text": text, "legend_image": legend_image},
                    metadata={"_position": position}
                )
                block.estimated_height = estimate_block_height(block)
                blocks.append(block)

        content = re.sub(pattern, '', content, flags=re.DOTALL)
        return content

    def _extract_text_chart_rows(self, content: str, blocks: List[Block]) -> str:
        """Extract text-chart row blocks (minipage pairs with text and chart)"""
        # Pattern for two minipages with text and chart
        pattern = r'\\begin\{minipage\}\[t\]\{(0\.\d+)\\textwidth\}(.*?)\\end\{minipage\}%?\s*\\hfill\s*\\begin\{minipage\}\[t\]\{(0\.\d+)\\textwidth\}(.*?)\\includegraphics\[.*?\]\{([^}]+)\}(.*?)\\end\{minipage\}'

        for match in re.finditer(pattern, content, re.DOTALL):
            position = match.start()
            text_width = float(match.group(1))
            text_content = match.group(2)
            chart_width = float(match.group(3))
            chart_file = match.group(5)

            # Skip if this looks like a subheader legend (already extracted)
            if 'height=1cm' in match.group(0):
                continue

            # Clean up text content
            text = text_content
            text = re.sub(r'\\vspace\{[^}]+\}', '', text)
            text = re.sub(r'\\fontsize\{\d+\}\{\d+\}\\selectfont', '', text)
            text = re.sub(r'\\centering', '', text)
            text = text.strip()

            # Extract font size if present
            font_match = re.search(r'\\fontsize\{(\d+)\}\{(\d+)\}', text_content)
            font_size = int(font_match.group(1)) if font_match else 10
            line_height = int(font_match.group(2)) if font_match else 13

            if text and chart_file:
                block = Block(
                    type=BlockType.TEXT_CHART_ROW,
                    content={"text": text, "chart_file": chart_file},
                    metadata={
                        "_position": position,
                        "text_width": text_width,
                        "chart_width": chart_width,
                        "font_size": font_size,
                        "line_height": line_height
                    }
                )
                block.estimated_height = estimate_block_height(block)
                blocks.append(block)

        content = re.sub(pattern, '', content, flags=re.DOTALL)
        return content

    def _extract_charts(self, content: str, blocks: List[Block]) -> str:
        """Extract standalone chart blocks"""
        # Pattern for centered charts
        pattern = r'\\noindent\s*\\includegraphics\[([^\]]*)\]\{([^}]+)\}'

        for match in re.finditer(pattern, content, re.DOTALL):
            position = match.start()
            options = match.group(1)
            image_file = match.group(2)

            # Parse width from options
            width_match = re.search(r'width=([^,\]]+)', options)
            width = width_match.group(1) if width_match else "\\linewidth"
            if width == "\\linewidth":
                width = "linewidth"

            block = Block(
                type=BlockType.CHART,
                content=image_file,
                metadata={"_position": position, "width": width, "alignment": "center"}
            )
            block.estimated_height = estimate_block_height(block)
            blocks.append(block)

        content = re.sub(pattern, '', content, flags=re.DOTALL)

        # Also check for charts in center environment
        center_pattern = r'\\begin\{center\}\s*\\includegraphics\[([^\]]*)\]\{([^}]+)\}\s*\\end\{center\}'
        for match in re.finditer(center_pattern, content, re.DOTALL):
            position = match.start()
            options = match.group(1)
            image_file = match.group(2)

            width_match = re.search(r'width=([^,\]]+)', options)
            width = width_match.group(1) if width_match else "\\linewidth"
            if width == "\\linewidth":
                width = "linewidth"

            block = Block(
                type=BlockType.CHART,
                content=image_file,
                metadata={"_position": position, "width": width, "alignment": "center"}
            )
            block.estimated_height = estimate_block_height(block)
            blocks.append(block)

        content = re.sub(center_pattern, '', content, flags=re.DOTALL)
        return content

    def _extract_bullet_lists(self, content: str, blocks: List[Block]) -> str:
        """Extract bullet list blocks"""
        pattern = r'\\begin\{itemize\}(.*?)\\end\{itemize\}'

        for match in re.finditer(pattern, content, re.DOTALL):
            position = match.start()
            inner_content = match.group(1)

            # Extract items
            items = re.findall(r'\\item\s*(.*?)(?=\\item|$)', inner_content, re.DOTALL)
            items = [self._clean_text(item.strip()) for item in items if item.strip()]

            if items:
                block = Block(
                    type=BlockType.BULLET_LIST,
                    content=items,
                    metadata={"_position": position}
                )
                block.estimated_height = estimate_block_height(block)
                blocks.append(block)

        content = re.sub(pattern, '', content, flags=re.DOTALL)
        return content

    def _extract_titles(self, content: str, blocks: List[Block]) -> str:
        """Extract title blocks"""
        # Pattern for titles with color and optional underline
        pattern = r'\\noindent\s*\{\\fontsize\{(\d+)\}\{(\d+)\}\\selectfont\s+\\textbf\{\\color\{(\w+)\}(?:\s*\\underline\{)?([^}]+)\}?\}\}'

        for match in re.finditer(pattern, content, re.DOTALL):
            position = match.start()
            font_size = int(match.group(1))
            color = match.group(3)
            title_text = match.group(4).strip()

            # Determine level from font size
            if font_size >= 20:
                level = 1
            elif font_size >= 11:
                level = 2
            else:
                level = 3

            # Check for underline
            underline = "\\underline{" in match.group(0)

            block = Block(
                type=BlockType.TITLE,
                content=title_text,
                metadata={
                    "_position": position,
                    "level": level,
                    "color": color,
                    "underline": underline
                }
            )
            block.estimated_height = estimate_block_height(block)
            blocks.append(block)

        content = re.sub(pattern, '', content, flags=re.DOTALL)
        return content

    def _extract_paragraphs(self, content: str, blocks: List[Block]) -> str:
        """Extract paragraph blocks"""
        # Pattern for paragraphs with fontsize
        pattern = r'\\noindent\s*\{\\fontsize\{(\d+)\}\{(\d+)\}\\selectfont(?:\s*\\color\{(\w+)\})?(.*?)\}'

        for match in re.finditer(pattern, content, re.DOTALL):
            position = match.start()
            font_size = int(match.group(1))
            line_height = int(match.group(2))
            color = match.group(3) or "black"
            text = match.group(4).strip()

            # Skip if already processed as title
            if '\\textbf{\\color{' in text:
                continue

            # Check for bold
            bold = '\\textbf{' in text
            if bold:
                text = re.sub(r'\\textbf\{(.*?)\}', r'\1', text, flags=re.DOTALL)

            text = self._clean_text(text)

            if text and len(text) > 5:
                block = Block(
                    type=BlockType.PARAGRAPH,
                    content=text,
                    metadata={
                        "_position": position,
                        "font_size": font_size,
                        "line_height": line_height,
                        "color": color,
                        "bold": bold
                    }
                )
                block.estimated_height = estimate_block_height(block)
                blocks.append(block)

        content = re.sub(pattern, '', content, flags=re.DOTALL)
        return content

    def _clean_text(self, text: str) -> str:
        """Clean up extracted text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text


def parse_section_file(filepath: str, section_type: SectionType = None) -> BlockManager:
    """Parse a LaTeX section file into blocks"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    parser = LaTeXParser(section_type)
    blocks = parser.parse(content)

    manager = BlockManager(section_type or SectionType.ANALYSIS_OVERALL)
    manager.blocks = blocks

    return manager


def save_section_file(filepath: str, manager: BlockManager) -> None:
    """Save blocks back to LaTeX file"""
    latex_content = manager.generate_latex()

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(latex_content)
