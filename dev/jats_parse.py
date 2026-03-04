"""
jats_parse.py -- a kludge to convert a fulltext jats xml
object into a fulltext data model in jsonschema format
Note: requires ADSIngestParser
"""
import json
import re
from bs4 import BeautifulSoup
from adsingestp.parsers.jats import JATSParser

regex_multiple_sp = re.compile(r" +")
def clean_spaces(text):
    cleantext = text.replace("\n", " ")
    cleantext = regex_multiple_sp.sub(" ", cleantext)
    cleantext = cleantext.lstrip().rstrip()
    nbtext = cleantext.replace(" ", "")
    if nbtext:
        return cleantext

def build_recdata(infile):
    recdata = {
        "loadLocation": infile,
        "loadFormat": "JATS",
        "loadType": "fromFile",
        "dataType": "fulltext",
        "UUID": "0000-1111-2222-3333",
        "masterRecord": "SciX:123abcPDQ",
        "parsedTime": "2025-03-20T12:00:00.000000Z",
        "createdTime": "2025-03-20T12:00:00.000000Z",
        "recordOrigin": "Publisher"
    }
    return recdata
def get_reflist(soup):
    try:
        allref = soup.find("ref-list")
        reflist = allref.find_all("ref")
        ref_list = []
        for r in reflist:
            ref = dict()

            ref_id = r["id"]
            if ref_id:
                ref["id"] = ref_id
            xml = str(r)
            if xml:
                ref["xml"] = xml
            doi = r.find("pub-id", attrs={"pub-id-type": "doi"})
            if doi:
                ref["doi"] = doi.text

            if ref:
                ref_list.append(ref)
        return ref_list
    except Exception as err:
        print("Reflist died: %s" % err)
        
def get_footnotes(soup):
    try:
        xrefs = soup.find_all("xref", attrs={"ref-type":"fn"})
        footnotes = soup.find_all("fn")
        footnote_dict = {}
        fn_list = []
        for f in footnotes:
            atext = f.text
            fn_id = f["id"]
            if fn_id and atext:
                fn = {fn_id: clean_spaces(atext)}
                footnote_dict.update(fn)
        for x in xrefs:
            rid = x["rid"]
            label = clean_spaces(x.extract().text)
            text = footnote_dict.get(rid, "")
            if text:
                text = text.replace(label, "")
            fn = {"id": rid, "label": label.lstrip().rstrip(), "text": text}
            if fn:
                fn_list.append(fn)
        return fn_list
    except Exception as err:
        print("Footnotes died: %s" % err)

def get_figures(soup):
    try:
        figures = soup.find_all("fig")
        fig_list = []
        for f in figures:
            fig_id = f["id"]
            label = f.label
            caption = f.caption
            fig = dict()
            if fig_id:
                fig["id"] = fig_id
            if label:
                fig["label"] = label.text
            if caption:
                fig["caption"] = caption.text
            if fig:
                fig_list.append(fig)
            f.decompose()
        return fig_list
    except Exception as err:
        print("Figs died: %s" % err)

def get_tables(soup):
    try:
        tables = soup.find_all("table-wrap")
        table_list = []
        for t in tables:
            table_id = t["id"]
            label = t.label
            caption = t.caption
            data = t.table
            table = dict()
            if table_id:
                table["id"] = table_id
            if label:
                table["label"] = label.text
            if caption:
                table["caption"] = caption.text
            if data:
                table["data"] = str(data)
            if table:
                table_list.append(table)
            t.decompose()
        return table_list
    except Exception as err:
        print("Tables died: %s" % err)

def get_bibrefs(soup):
    try:
        refs = soup.find_all("xref", attrs={"ref-type": "bibr"})
        bibref_list = []
        for b in refs:
            bibr = {}
            refid = b["rid"]
            if refid:
                bibr["id"] = refid
            atext = b.text
            if atext:
                bibr["atext"] = atext
            if bibr:
                bibref_list.append(bibr)
           
        return bibref_list
    except Exception as err:
        print("Bibrefs died: %s" % err)

def get_sections(soup, sectype="sec"):
    try:
        sections = soup.find_all(sectype)
        sec_list = []
        for s in sections:
            try:
                sec_id = s.get("id", "")
            except:
                sec_id = ""
            try:
                sec_type = s["sec-type"]
            except:
                sec_type = ""
            title = s.find("title")
            label = s.find("label")
            subsections = get_sections(s)
            figures = get_figures(s)
            tables = get_tables(s)
            footnotes = get_footnotes(s)
            bibrefs = get_bibrefs(s)

            sec = dict()
            if sec_id:
                sec["id"] = sec_id
            if sec_type:
                sec["type"] = sec_type
            if title:
                sec["section_title"] = title.extract().text
            if label:
                sec["label"] = label.extract().text
            if figures:
                sec["figures"] = figures
            if tables:
                sec["tables"] = tables
            if subsections:
                sec["subsections"] = subsections
            if bibrefs:
                sec["bibrefs"] = bibrefs
            if footnotes:
                sec["footnotes"] = footnotes
        
            cleantext = clean_spaces(s.text)
            if cleantext:
                sec["atext"] = cleantext
            if sec:
                sec_list.append(sec)
            s.decompose()
        return sec_list
    except Exception as err:
        print("Sections died: %s" % err)

def get_facilities(soup):
    try:
        facils = soup.find_all("named-content", attrs={"content-type": "facility"})
        fac_list = []
        for f in facils:
            fac = f.text
            if fac:
                fac_list.append(fac)
        return fac_list
    except Exception as err:
        print("Facilities died: %s" % err)

def get_ack(soup):
    try:
        ack = soup.find("ack")
        ack_dict = {}
        fac = get_facilities(ack)
        if fac:
            ack_dict["facilities"] = fac
        title = ack.find("title")
        if title:
            ack_dict["title"] = title.extract().text
        text = clean_spaces(ack.text)
        if text:
            ack_dict["text"] = text
          
        return ack_dict
    except Exception as err:
        print("Ack died: %s" % err)

def get_fngroup(soup):
    try:
        footnotes = soup.find_all("fn")
        
        fn_list = []
        for f in footnotes:
            fn = dict()
            id = f.get("id", "")
            label = f.find("label").extract().text
            text = f.text
            text = clean_spaces(text.replace(label,""))
            if id:
                fn["id"] = id
            if label:
                fn["label"] = label
            if text:
                fn["text"] = text
            if fn:
                fn_list.append(fn)
        return fn_list
    except Exception as err:
        print("fngroup died: %s" % err)
            

def main():
    #infile = "files/aa53501-24.xml"
    infile = "files/apj_976_1_106.xml"
    with open(infile, "r") as fx:
        rawData = fx.read()


    # this is where we write the data
    output = dict()

    # article metadata -- just use JATSParser!
    parser = JATSParser()
    meta = parser.parse(rawData, bsparser="lxml-xml")

    title = meta.get("title", "")
    if title:
        output["title"] = title

    authors = meta.get("authors", [])
    if authors:
        output["authors"] = authors

    keywords = meta.get("keywords", [])
    if keywords:
        output["keywords"] = keywords

    cpyr = meta.get("copyright", "") 
    if cpyr:
        output["copyright"] = cpyr

    oa = meta.get("openAccess", "")
    if oa:
        output["openAccess"] = oa

    pids = meta.get("persistentIDs", [])
    if pids:
        output["persistentIDs"] = pids

    publication = meta.get("publication", "")
    if publication:
        output["publication"] = publication

    pubdate = meta.get("pubDate", "")
    if pubdate:
        output["pubDate"] = pubdate

    funding = meta.get("funding", [])
    if funding:
        output["funding"] = funding



    # now start parsing it as fulltext...
    soup = BeautifulSoup(rawData, "lxml-xml")

    # abstract from front matter
    front = soup.find("front")
    abstract = get_sections(front, sectype="abstract")     
    if abstract:
        output["abstract"] = abstract

    # paper body
    body = soup.find("body")

    #try:
    #    get_footnotes(body)
    #except Exception as err:
    #    print("well, test: %s" % err)

    body = get_sections(body)
    if body:
        output["body"] = body


    # paper backmatter
    backmatter = soup.find("back")

    appendices = get_sections(backmatter, sectype="app")
    acknowledgements = get_ack(backmatter)
    references = get_reflist(backmatter)
    fngroup = backmatter.find("fn-group")
   
    if appendices:
        output["appendices"] = appendices

    if acknowledgements:
        output["acknowledgements"] = acknowledgements

    if references:
        output["references"] = references
    if fngroup:
        output["footnote-table"] = get_fngroup(fngroup)

    output["recordData"] = build_recdata(infile)

    if output:
        with open(infile+".json", "w") as fj:
            fj.write("%s\n" % json.dumps(output, indent=2, sort_keys=True))
    else:
        print("I got nothing. :(")


if __name__ == "__main__":
    main()


