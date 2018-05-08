"""
Author:         Dominik Müller
Created:        May 7 00:06 2018
Dependencies:   Python 3.x
                pandas
                Bio
Purpose:        Protein Data Science
                Analysis of evolutionary sequences of transmembrane proteins
Credits:        Mark Teese
                Martin Ortner
                Shenger Wang
                Rimma Jenske
                Dominik Müller
License         Released under the permissive MIT license.
"""
import csv
import logging
import os
import korbinian
import pandas as pd
import sys
from Bio.Blast import NCBIWWW
from Bio.Blast.Applications import NcbiblastpCommandline
# import debugging tools
from korbinian.utils import pr, pc, pn, aaa

def run_BLAST_online(pathdict, s, logging):
    """From the list of proteins in csv format, begins online BLASTp searches for homologous proteins

    Parameters
    ----------
    pathdict : dict
        Dictionary of the key paths and files associated with that List number.
    s : dict
        Settings dictionary extracted from excel settings file.
    logging : logging.Logger
        Logger for printing to console and logfile.

    Saved Files and Figures
    -----------------------
    PROTEIN_NAME.blast_result.xml : xml file containing BLASTp hits
        (e.g. A2A2V5.blast_result.xml)
    """
    logging.info("~~~~~~~~~~~~                 starting running BLASTp via online API                 ~~~~~~~~~~~~")

    #IF blast directory doesn't exist -> create blast directory in the data(base) directory
    blast_dir = os.path.join(s["data_dir"], "blast")
    if not os.path.exists(blast_dir):
        os.makedirs(blast_dir)

    #Obtain protein data frame
    df = pd.read_csv(pathdict["list_csv"], sep = ",", quoting = csv.QUOTE_NONNUMERIC, index_col = 0)

    #Obtain blast settings from the settings file
    evalue = s["blast_Evalue"];
    hitsize = s["blast_max_hits"]

    #iterate over each protein
    for acc in df.index:
        #Variable initializations for current protein
        protein_name = df.loc[acc, 'protein_name']
        input_sequence = df.loc[acc, 'full_seq']
        query = ">" + protein_name + "\n" + input_sequence + "\n"

        #Initialize file system in database/blast directory
        blast_proteinID_dir = os.path.join(s["data_dir"], "blast", protein_name[:2])
        if not os.path.exists(blast_proteinID_dir):
            os.makedirs(blast_proteinID_dir)
        output_file = os.path.join(s["data_dir"], "blast", protein_name[:2], protein_name + ".blast_result.xml")

        #Run BLASTp search
        logging.info("Run BLASTp online search for protein:" + "\t" + protein_name)
        blast_result = NCBIWWW.qblast("blastp", "nr", query, expect=evalue,  hitlist_size=hitsize)

        #Write BLASTp result into file
        with open(output_file, "w") as blast_result_writer:
            blast_result_writer.write(blast_result.read())
        blast_result_writer.close()

    logging.info("~~~~~~~~~~~~                 finished BLASTp search                 ~~~~~~~~~~~~")



def run_BLAST_local(pathdict, s, logging):
    """From the list of proteins in csv format, begins local BLASTp searches for homologous proteins

    Parameters
    ----------
    pathdict : dict
        Dictionary of the key paths and files associated with that List number.
    s : dict
        Settings dictionary extracted from excel settings file.
    logging : logging.Logger
        Logger for printing to console and logfile.

    Saved Files and Figures
    -----------------------
    PROTEIN_NAME.blast_result.xml : xml file containing BLASTp hits
        (e.g. A2A2V5.blast_result.xml)
    """
    logging.info("~~~~~~~~~~~~                 starting running BLASTp locally                 ~~~~~~~~~~~~")

    #IF blast directory doesn't exist -> create blast directory in the data(base) directory
    blast_dir = os.path.join(s["data_dir"], "blast")
    if not os.path.exists(blast_dir):
        os.makedirs(blast_dir)

    #Obtain protein data frame
    df = pd.read_csv(pathdict["list_csv"], sep = ",", quoting = csv.QUOTE_NONNUMERIC, index_col = 0)

    #Obtain blast settings from the settings file
    evalue = s["blast_Evalue"];
    hitsize = s["blast_max_hits"]
    database = s["BLAST_local_DB"]

    #iterate over each protein
    for acc in df.index:
        #Variable initializations for current protein
        protein_name = df.loc[acc, 'protein_name']
        input_sequence = df.loc[acc, 'full_seq']
        query = ">" + protein_name + "\n" + input_sequence + "\n"

        #Initialize file system in database/blast directory
        blast_proteinID_dir = os.path.join(s["data_dir"], "blast", protein_name[:2])
        if not os.path.exists(blast_proteinID_dir):
            os.makedirs(blast_proteinID_dir)
        output_file = os.path.join(s["data_dir"], "blast", protein_name[:2], protein_name + ".blast_result.xml")

        #Run BLASTp search and write results into the database/blast directory
        logging.info("Run BLASTp local search for protein:" + "\t" + protein_name)
        blastp_cline = NcbiblastpCommandline(db=database, evalue=0.001, outfmt=5, out=output_file)
        out, err = blastp_cline(stdin=query)

        #DEBUGGING
        logging.warning(out)

    logging.info("~~~~~~~~~~~~                 finished BLASTp search                 ~~~~~~~~~~~~")
