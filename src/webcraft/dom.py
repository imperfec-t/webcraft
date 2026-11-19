"""A forgiving HTML tree built on html.parser (standard library only)."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Dict, Iterator, List, Optional, Union

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
        "source", "track", "wbr"}
BLOCK = {"address", "article", "aside", "blockquote", "div", "dl", "fieldset", "figure", "footer",
         "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "main", "nav", "ol", "p", "pre",
         "section", "table", "ul"}
SELF_CLOSING_SIBLINGS = {"li", "p", "option", "dt", "dd", "tr", "td", "th"}
NO_TEXT = {"script", "style", "noscript", "template", "svg"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "line")

    def __init__(self, tag: str, attrs: Optional[Dict[str, str]] = None,
                 parent: Optional["Node"] = None, line: int = 0):
        self.tag = tag
        self.attrs = attrs or {}
        self.children: List[Union["Node", str]] = []
        self.parent = parent
        self.line = line

    def get(self, key: str, default: str = "") -> str:
        return self.attrs.get(key, default)

    def has(self, key: str) -> bool:
        return key in self.attrs

    @property
    def classes(self) -> List[str]:
        return self.get("class").split()

    def elements(self) -> List["Node"]:
        return [c for c in self.children if isinstance(c, Node)]

    def iter(self) -> Iterator["Node"]:
        yield self
        for c in self.children:
            if isinstance(c, Node):
                yield from c.iter()

    def find_all(self, *tags: str) -> List["Node"]:
        tags_set = set(tags)
        return [n for n in self.iter() if n.tag in tags_set and n is not self]

    def find(self, *tags: str) -> Optional["Node"]:
        for n in self.iter():
            if n is not self and n.tag in tags:
                return n
        return None

    def ancestors(self) -> Iterator["Node"]:
        p = self.parent
        while p is not None:
            yield p
            p = p.parent

    def text(self) -> str:
        parts: List[str] = []

        def walk(n: "Node"):
            for c in n.children:
                if isinstance(c, str):
                    parts.append(c)
                elif c.tag not in NO_TEXT:
                    walk(c)
                    if c.tag in BLOCK or c.tag == "br":
                        parts.append(" ")

        walk(self)
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def raw_text(self) -> str:
        """Text including script and style content."""
        return "".join(c if isinstance(c, str) else c.raw_text() for c in self.children)

    def snippet(self, limit: int = 90) -> str:
        keep = ("id", "class", "src", "href", "name", "type", "rel", "property", "content", "action")
        attrs = " ".join(f'{k}="{v}"' for k, v in self.attrs.items() if k in keep and v)[:limit]
        return f"<{self.tag}{' ' + attrs if attrs else ''}>"

    def __repr__(self) -> str:
        return self.snippet()


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.cur = self.root

    def _open(self, tag: str):
        if self.cur.tag == tag and tag in SELF_CLOSING_SIBLINGS:
            self.cur = self.cur.parent or self.root
        elif self.cur.tag == "p" and tag in BLOCK:
            self.cur = self.cur.parent or self.root

    def handle_starttag(self, tag, attrs):
        self._open(tag)
        node = Node(tag, {k.lower(): (v if v is not None else "") for k, v in attrs}, self.cur,
                    self.getpos()[0])
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self._open(tag)
        node = Node(tag, {k.lower(): (v if v is not None else "") for k, v in attrs}, self.cur,
                    self.getpos()[0])
        self.cur.children.append(node)

    def handle_endtag(self, tag):
        n: Optional[Node] = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse(html: str) -> Node:
    b = _Builder()
    try:
        b.feed(html)
        b.close()
    except Exception:  # html.parser is lenient; never let a bad page crash an audit
        pass
    return b.root
