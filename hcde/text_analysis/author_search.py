"""
Some Python code for taking a certain CHI paper, splitting it into citations,
sentences, and authors, generating an authorship connectivity network, and
linking citations and sentences. Used for Empirical Traditions HCDE grad
class.

If you are using Python 3, you will need to install pdfminer.six instead
of pdfminer. Graphs visualized outside of python with VOSviewer..
"""

import unicodedata
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO
from networkx.algorithms import community
from collections import defaultdict


def convert_pdf_to_txt(pdf_filepath, output_filepath, password='', max_pages=0, caching=True, page_num=set()):
     
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()

    # Change codec if needed.
    codec = 'utf-8'  # 'utf16','utf-8'
    with StringIO() as return_string, open(pdf_filepath, 'rb') as open_file, \
            open(output_filepath, 'wb') as out_file:
        with TextConverter(rsrcmgr, return_string, codec=codec, laparams=laparams) as device:
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            for page in PDFPage.get_pages(open_file, page_num, maxpages=max_pages, password=password, caching=caching, check_extractable=True):
                interpreter.process_page(page)

            paper_string = return_string.getvalue()
            paper_string, references, sentences, author_clusters = clean_paper_text(paper_string)
            out_file.write(paper_string.encode('utf-8'))
            # print(paper_string)
            return paper_string


def remove_accents(input_str):

    """ This function is used because either OCR or our authors do not
        consistently accent citation authors' names.
    """

    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


def clean_paper_text(input_string):

    # The problem with splitting by periods is that periods are used for more than just
    # ending sentences, hence the last replaces..
    input_string = input_string.replace('\n', ' ').replace('- ', '').replace('  ', ' ').replace('vs.', 'vs') \
        .replace('e.g.', 'e.g').replace(').', ')').replace('i.e.', 'i.e')

    before_references, after_references = str.split(input_string, 'REFERENCES')    

    # Split references
    individual_references = str.split(after_references, '[')
    reference_dict = {}
    for item in individual_references:
        try:
            citation_num, citation = str.split(item, '] ')
            reference_dict[citation_num] = citation
            # print(citation_num, '\n', reference_dict[citation_num])
        except:
            continue

    # Split authors, and add them to an authorship graph.
    author_dict = {}
    all_authors = []
    author_graphs = []
    for key, item in reference_dict.items():
        author_list = str.split(item, '.')[0]
        author_list = str.split(author_list, ',')
        corrected_author_list = []
        for author in author_list:

            if 'and' in author:
                authors = [remove_accents(x.strip()) for x in str.split(author, ' and ') if x != '']
                corrected_author_list += authors
            else:
                corrected_author_list += [remove_accents(author.strip())]
        author_dict[key] = corrected_author_list
        # print(corrected_author_list)
        all_authors += corrected_author_list

        G = nx.Graph()
        for author in corrected_author_list:
            G.add_node(author)
        for author_1 in corrected_author_list:
            for author_2 in corrected_author_list:
                G.add_edge(author_1, author_2)
        author_graphs += [G]

    # Combine all the authorship graphs into a union graph, and save out the
    # graph. I viewed them with a software called VOSviewer, which I don't think
    # is the best software available.
    final_graph = nx.Graph()
    for graph in author_graphs:
        final_graph = nx.compose(final_graph, graph)
    nx.write_pajek(final_graph, 'test_graph.net')
    all_authors = np.unique(all_authors)
    connected_author_components = list(nx.connected_components(final_graph))

    # Split sentences
    sentence_list = []
    sentences = str.split(before_references, '. ')
    for sentence_num, item in enumerate(sentences):
        if item == '':
            continue
        sentence_list += [item]
        # print(sentence_num, item)

    # Match sentences to metadata.
    # Gotta be a better way to do this with, uh, regular expressions
    # Or something.
    sentence_metadata_dict = {}
    for idx, sentence in enumerate(sentences):
        metadata = {}
        metadata['authors'] = []
        if '[' in sentence:
            sentence_split = str.split(sentence, '[')[1:]
            all_references = []
            for subsentence in sentence_split:
                reference_split = str.split(subsentence, ']')[0].replace(' ', '')
                if reference_split.isalpha():
                    # To avoid words in brackets.
                    continue
                comma_split = str.split(reference_split, ',')
                all_references += comma_split
            if all_references == []:
                continue
            metadata['references'] = all_references
            for reference in all_references:
                metadata['authors'] += author_dict[reference]
            sentence_metadata_dict[idx] = metadata

    # Match clusters to sentences. Variables kind of getting
    # complicated here.
    cluster_dict = defaultdict(list)
    for idx, cluster in enumerate(connected_author_components):
        print(idx, cluster)
        for key, sentence_metadata in sentence_metadata_dict.items():
            if len(cluster.intersection(set(sentence_metadata['authors']))) > 0:
                cluster_dict[idx] += [key]
    print(cluster_dict)

    return input_string, reference_dict, sentence_list, connected_author_components


# convert pdf file text to string and save as a text_pdf.txt file
def save_convert_pdf_to_txt(self):
    content = self.convert_pdf_to_txt()
    txt_pdf = open('text_pdf.txt', 'wb')
    txt_pdf.write(content.encode('utf-8'))
    txt_pdf.close()


if __name__ == '__main__':
    pdfConverter = convert_pdf_to_txt(pdf_filepath='../../Readings/Voice_User_Interfaces_in_Schools.pdf',
            output_filepath='test_text.txt')