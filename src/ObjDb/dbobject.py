"""
 Copyright (C) 2014 the original author or authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


@author: Barry Weinstein
"""

import re

def newFrom(objtype, objhsh, prettylines):
    """Factory method to construct a concrete instance of Dbobj having type objtype"""
    
    if objtype == 'tag':
        return Tag(objtype, objhsh, prettylines)
    elif objtype == 'commit':
        return Commit(objtype, objhsh, prettylines)
    elif objtype == 'tree':
        return Tree(objtype, objhsh, prettylines)
    elif objtype == 'blob':
        return Blob(objtype, objhsh, prettylines)
    else:
        raise Exception("unknown object type - " + objtype)

def part(line, idx):
    """Convenience language to return a part of a line after it's split at whitespace"""
    parts = re.split("\s", line)
    if idx >= len(parts):
        return None
    return parts[idx]

def q(astring):
    """Convenience language to return astring surrounded by quotes"""
    return "\"" + astring + "\""

def wl(f, string):
    f.write(string + "\n")

class Dbobj(object):
    """Any database object"""
    
    def __init__(self, objtype, objhsh, prettylines):
        # a dictionary of hashes to Refs interpreted from my prettylines
        self.references = {}
        # a rename without content change will be the same blob. The two different
        # containing tree-ish's will reference the blob by different names
        self.referencedbynames = set()
        # provided by Dag
        self.objsReferring2Me = []
        self.objsIReference = []

        self.objtype = objtype
        self.objhsh = objhsh
        self.prettylines = prettylines      
    def noticeReference(self, ref):
        """Notice my reference during construction"""
        self.references[ref.hsh] = ref  
    def acceptReferenced(self, dbobj):
        """Accept that I reference dbobj since the DAG told me so"""
        self.objsIReference.append(dbobj)
    def acceptReferrer(self, dbobj):
        """Accept that dbobj refers to me since the DAG told me so"""
        self.objsReferring2Me.append(dbobj) 
    def present(self):
            print("****\n" + self.objtype + " " + self.objhsh)
    def dotDescribe(self):
        color = " [color=grey]"
        if self.objtype == 'commit':
            color = " [color=red]";
        elif self.objtype == 'tree':
            color = " [color=green]"
        elif self.objtype == 'tag':
            color = " [color=blue]"
        elif self.objtype == 'blob':
            color = " [color=grey]"
        return q(self.id()) + color
    def id(self):
        return self.objhsh[0:6]
           
class Tag(Dbobj):
    """A subclass of Dbobj abstracting a tag in a Git repository"""

    def __init__(self, objtype, objhsh, prettylines):
        super(Tag, self).__init__(objtype, objhsh, prettylines)
        for line in prettylines:
            part0 = part(line, 0)
            if part0 == 'tag':
                self.label = part(line, 1)
            if part0 == 'object':
                objhash = part(line, 1)
                self.noticeReference(Ref(objhash))
    def present(self):
            super(Tag, self).present()
            print("-> " + self.prettylines[1]) 
            print("-> " + self.prettylines[2]) 
    
class Commit(Dbobj):
    """A subclass of Dbobj abstracting a commit in a Git repository"""

    def __init__(self, objtype, objhsh, prettylines):
        super(Commit, self).__init__(objtype, objhsh, prettylines)
        for line in prettylines:
            part0 = part(line, 0)
            if part0 == 'parent' or part0 == 'tree':
                objhash = part(line, 1)
                self.noticeReference(Ref(objhash))
                
    def present(self):
        """Send to stdout a textual representation of this object"""

        super(Commit, self).present()
        print("-> " + self.prettylines[0])
        print("-> " + self.prettylines[1])
        readyforcomment = False 
        for linenum in range(2, len(self.prettylines)):
            if readyforcomment:
                print(self.prettylines[linenum])
                continue
            if len(self.prettylines[linenum]) == 0:
                readyforcomment = True

class Tree(Dbobj):
    """A subclass of Dbobj abstracting a directory version in a Git repository"""

    def __init__(self, objtype, objhsh, prettylines):
        super(Tree, self).__init__(objtype, objhsh, prettylines)
        for line in prettylines:
            part1 = part(line, 1)
            if part1 == 'blob' or part1 == 'tree':
                objhash = part(line, 2)
                referencedbyname = part(line, 3)
                self.noticeReference(Ref(objhash, referencedbyname))
    def present(self):
        """Send to stdout a textual representation of this object"""

        super(Tree, self).present()
        if len(self.referencedbynames) > 0:
            print("known as " + str(self.referencedbynames))
        else:
            print("root tree")
        for line in self.prettylines:
            if len(line) == 0:
                continue
            print("-> " + line)
            
class Blob(Dbobj):
    """A subclass of Dbobj abstracting a file versioned in a Git repository"""
    
    def __init__(self, objtype, objhsh, prettylines):
        super(Blob, self).__init__(objtype, objhsh, prettylines)
        self.content = prettylines
    
    def present(self):
        """Send to stdout a textual representation of this object"""

        super(Blob,self).present()
        print("known as " + str(self.referencedbynames));
        print("-> first line: " + self.prettylines[0])

class Ref(object):
    """An abstraction of a relationship between two objects in the object database
    
    This is introduced hold the various names that database objects are referred to.
    """
    
    def __init__(self, hsh, referencedbyname=None):
        self.hsh = hsh
        self.nameused = referencedbyname

class Dag(object):
    """Graph of database object relationships"""
    
    def __init__(self, dbobjs):
        self.edges = []
        self.edgesfrom = {}
        self.edgesto= {}
        self.dbobjs = dbobjs
        for referrer in dbobjs:
            for referenced in dbobjs:
                if referenced.objhsh in referrer.references.keys():
                    referrer.acceptReferenced(referenced)
                    referenced.acceptReferrer(referrer)
                    referencedbyname = referrer.references[referenced.objhsh].nameused
                    referenced.referencedbynames.add(referencedbyname)
                    edge = Edge(referrer, referenced, referencedbyname)
                    self.edges.append(edge)
                    self.edgesfrom[referrer] = edge
                    self.edgesto[referenced] = edge
    
    def dotDescribe(self, outfile):
        """Send to outfile DOT language instructions to render this entire DAG"""
        
        dot = None
        try:
            if outfile:
                dot = open(outfile, 'w+')
            else:
                dot = open("/Users/bweinste/Desktop/git.dot", 'w+')
            self.dotDescribeToFile(dot)
        finally:
#             dot.close()
            pass
            
    def dotDescribeToFile(self, dot):
        wl(dot, "digraph graphname {")
        for dbobj in self.dbobjs:
            wl(dot, dbobj.dotDescribe())
        for edge in self.edges:
            wl(dot, edge.dotDescribe())
        wl(dot, "}")

class Edge(object):
    """A directed edge of an acyclic graph"""
    def __init__(self, beginning, ending, referencename):
        self.beginning = beginning
        self.ending = ending
        if not referencename:
            self.referencename = 'anonymous'
        else:
            self.referencename = referencename
    
    def dotDescribe(self):
        """Return a DOT language representation of this edge"""
        label = ""
        nm = self.referencename
        if nm != 'anonymous':
            label = " [label=\"" + nm +  "\"; fontsize=9]"
        beginning = q(self.beginning.id())
        ending = q(self.ending.id())
        return(beginning + " -> " + ending + label + ";")
