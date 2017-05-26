from scipy.stats import ttest_ind
import ast
import csv
import itertools
import korbinian
import korbinian.utils as utils
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd
import sys
import zipfile
import os
import pickle
import scipy
# import debugging tools
from korbinian.utils import pr, pc, pn, aaa

def save_figures_describing_proteins_in_list(pathdict, s, logging):
    logging.info("~~~~~~~~~~~~         starting run_save_figures_describing_proteins_in_list          ~~~~~~~~~~~~")
    # define save settings
    save_png = s["save_png"]
    save_pdf = s["save_pdf"]
    try:
        base_filepath = pathdict["single_list_fig_path"]
    except:
        logging.info("Rare bug related to 'not subscriptable' has occurred. Logging full pathdict and pathdict type:")
        logging.info(pathdict)
        logging.info(type(pathdict))

    list_number = s["list_number"]
    # set resolution for plots in png format
    dpi = 300
    plt.style.use('seaborn-whitegrid')

    # set default font size for plot
    fontsize = 8
    datapointsize = 8
    #alpha = 0.1
    color_list_TUM_blue = ['#0F3750', '#0076B8', '#9ECEEC']
    # letters for saving variations of a figure
    letters = list("abcdefghijk")
    # for xlim, use the min and max evolutionary distance settings for the full dataset
    # this is used for subsequent figures
    min_evol_distance = int((1 - s["max_ident"]) * 100)
    max_evol_distance = int((1 - s["min_ident"]) * 100)

    '''Prepare data for the following plots'''

    # load cr_summary file
    df_cr_summary = pd.read_csv(pathdict["list_cr_summary_csv"], sep=",", quoting=csv.QUOTE_NONNUMERIC, index_col=0, low_memory=False)
    if df_cr_summary.shape[0] < s["min_n_proteins_in_list"]:
        return "~~~~~~~~~~~~            run_save_figures skipped, only {} proteins in list           ~~~~~~~~~~~~".format(df_cr_summary.shape[0])

    sys.stdout.write('Preparing data for plotting'), sys.stdout.flush()
    # load summary file
    df_list = pd.read_csv(pathdict["list_csv"], sep=",", quoting=csv.QUOTE_NONNUMERIC, index_col=0, low_memory=False)

    if 'uniprot_KW' in df_list.columns:
        if not "uniprot_KW_for_analysis" in df_list.columns:
            raise ValueError("Please run keyword analysis.")

    # merge cr_summary and summary file, if columns are equal in both files, suffix _dfc will be added in cr_summary column names for backwards compatibility
    df = pd.merge(df_cr_summary, df_list, left_index=True, right_index=True, suffixes=('_dfc', ''))

    # create number of datapoint dependent alpha_dpd
    alpha_dpd = utils.calc_alpha_from_datapoints(df['AAIMON_mean_all_TMDs'])
    sys.stdout.write('\nopacity of datapoints: {a:.2f}\n'.format(a=alpha_dpd))
    # filter to remove proteins that have less than ~5 homologues
    # this is only important for the beta-barrel dataset, which has a lot of these proteins!
    min_n_homol = s["min_homol"]
    n_prot_before_n_homol_cutoff = df.shape[0]
    df = df.loc[df['AAIMON_n_homol'] >= min_n_homol]
    n_prot_after_n_homol_cutoff = df.shape[0]
    n_removed = n_prot_before_n_homol_cutoff - n_prot_after_n_homol_cutoff
    # if any proteins have been removed, then print the exact number.
    if n_removed >= 1:
        sys.stdout.write("-- {}/{} -- proteins were removed, as they contained less than {} valid homologues. "
              "Final number of proteins = {}".format(n_removed, n_prot_before_n_homol_cutoff, min_n_homol, n_prot_after_n_homol_cutoff))
        sys.stdout.flush()

    # open list_csv file
    #df_uniprot = pd.read_csv(pathdict["list_csv"], sep=",", quoting=csv.QUOTE_NONNUMERIC, index_col=0)

    prot_family_df_dict = {}
    list_prot_families = None
    if 'uniprot_KW' in df.columns:

        # create a new column showing whether the protein is a GPCR
        if "GPCR" not in df.columns:
            # convert the keywords from a stringlist to a python list
            if isinstance(df['uniprot_KW'][0], str):
                df['uniprot_KW'] = df['uniprot_KW'].apply(lambda x: ast.literal_eval(x))
            df['GPCR'] = df['uniprot_KW'].apply(lambda x: 'G-protein coupled receptor' in x)
            df['olfactory_receptor'] = df['prot_descr'].apply(korbinian.cons_ratio.keywords.KW_list_contains_any_desired_KW, args=(['Olfactory receptor'],))

        df_GPCR = df.loc[df['GPCR'] == True]
        # add the dataframe segments to a dictionary for easy access?
        prot_family_df_dict["df_GPCR"] = df_GPCR
        prot_family_df_dict["df_nonGPCR"] = df.loc[df['GPCR'] == False]
        prot_family_df_dict["df_olfactory_receptorGPCR"] = df_GPCR.loc[df_GPCR['olfactory_receptor'] == True]
        prot_family_df_dict["df_non_olfactory_receptorGPCR"] = df_GPCR.loc[df_GPCR['olfactory_receptor'] == False]
        list_prot_families = ["df_GPCR", "df_nonGPCR", "df_olfactory_receptorGPCR", "df_non_olfactory_receptorGPCR"]
    else:
        sys.stdout.write('No uniprot keywords available! cannot create figures 19-21 \n')


    # # save dataframe
    # df.to_csv(pathdict["base_filename_summaries"] + '_df_figs.csv', sep=",", quoting=csv.QUOTE_NONNUMERIC)

    # create binlist
    linspace_binlist = np.linspace(s["mp_smallest_bin"],
                                   s["mp_largest_bin"],
                                   s["mp_number_of_bins"])

    # add 30 as the last bin, to make sure 100% of the data is added to the histogram, including major outliers
    binlist = np.append(linspace_binlist, s["mp_final_highest_bin"])

    # create list of colours to use in figures
    colour_lists = utils.create_colour_lists()
    tableau20 = colour_lists['tableau20']

    # DEPRECATED?
    # # create dataframe mean_AAIMON_each_TM
    # df_mean_AAIMON_each_TM = pd.DataFrame()
    # # add AAIMON each TMD to dataframe
    # for acc in df.index:
    #     for TMD in ast.literal_eval(df.loc[acc, 'list_of_TMDs']):
    #         df_mean_AAIMON_each_TM.loc[acc, '{a}_AAIMON_mean'.format(a=TMD)] = df.loc[acc, '{b}_AAIMON_mean'.format(b=TMD)]

    # count the maximum number of TMDs (excluding signal peptides) in the dataset
    max_num_TMDs = df.number_of_TMDs_excl_SP.max()

    # make list_of_TMDs a python list
    df['list_of_TMDs'] = df['list_of_TMDs'].apply(lambda x: ast.literal_eval(x))
    # logging saved data types
    sys.stdout.write('\nSaving figures as: ')
    if s['save_pdf']:
        sys.stdout.write(' .pdf ')
    if s['save_png']:
        sys.stdout.write(' .png ')
    sys.stdout.write('\n')

    # for Figs 97 and 98 set data to 'None' not to load data twice
    #data = False
    #binned_data = False

    if s['Fig01_Hist_AAIMON_and_AASMON']:
        Fig_Nr = 1
        title = 'Mean ratios'
        Fig_name = 'List{:02d}_Fig01_Hist_AAIMON_and_AASMON'.format(list_number)
        # create a new figure
        fig, ax = plt.subplots()
        # create numpy array of membranous over nonmembranous conservation ratios (identity)
        hist_data_AAIMON_mean = np.array(df['AAIMON_mean_all_TMDs'].dropna())
        # use numpy to create a histogram
        freq_counts_I, bin_array_I = np.histogram(hist_data_AAIMON_mean, bins=binlist)
        # assuming all of the bins are exactly the same size, make the width of the column equal to 70% of each bin
        col_width = float('%0.3f' % (0.95 * (bin_array_I[1] - bin_array_I[0])))
        # when align='center', the central point of the bar in the x-axis is simply the middle of the bins ((bin_0-bin_1)/2, etc)
        centre_of_bar_in_x_axis = (bin_array_I[:-2] + bin_array_I[1:-1]) / 2
        # add the final bin, which is physically located just after the last regular bin but represents all higher values
        bar_width = centre_of_bar_in_x_axis[3] - centre_of_bar_in_x_axis[2]
        centre_of_bar_in_x_axis = np.append(centre_of_bar_in_x_axis, centre_of_bar_in_x_axis[-1] + bar_width)
        barcontainer_AAIMON_mean = ax.bar(left=centre_of_bar_in_x_axis, height=freq_counts_I,
                                          align='center', width=col_width, color="#0489B1",
                                          alpha=0.5)  # edgecolor='black',
        # create numpy array of normalised membranous over nonmembranous conservation ratios (identity)
        hist_data_AAIMON_n_mean = np.array(df['AAIMON_mean_all_TMDs_n'].dropna())
        # use numpy to create a histogram
        freq_counts_I, bin_array_I = np.histogram(hist_data_AAIMON_n_mean, bins=binlist)
        # assuming all of the bins are exactly the same size, make the width of the column equal to 70% of each bin
        col_width = float('%0.3f' % (0.95 * (bin_array_I[1] - bin_array_I[0])))
        # when align='center', the central point of the bar in the x-axis is simply the middle of the bins ((bin_0-bin_1)/2, etc)
        centre_of_bar_in_x_axis = (bin_array_I[:-2] + bin_array_I[1:-1]) / 2
        # add the final bin, which is physically located just after the last regular bin but represents all higher values
        bar_width = centre_of_bar_in_x_axis[3] - centre_of_bar_in_x_axis[2]
        centre_of_bar_in_x_axis = np.append(centre_of_bar_in_x_axis, centre_of_bar_in_x_axis[-1] + bar_width)
        barcontainer_AAIMON_mean = ax.bar(left=centre_of_bar_in_x_axis, height=freq_counts_I,
                                          align='center', width=col_width, color="#EE762C",
                                          alpha=0.5)
        # create numpy array of membranous over nonmembranous conservation ratios (identity + similarity)
        hist_data_AASMON_mean = np.array(df['AASMON_ratio_mean_all_TMDs'].dropna())
        # use numpy to create a histogram
        freq_counts_S, bin_array_S = np.histogram(hist_data_AASMON_mean, bins=binlist)
        # barcontainer_S = axarr[row_nr,col_nr].bar(left=centre_of_bar_in_x_axis, height=freq_counts_S, align='center', width=col_width, color="#0101DF", edgecolor="#0101DF", alpha = 0.5)
        # create a line graph rather than a bar graph for the AASMON (ident + similarity)
        linecontainer_AASMON_mean = ax.plot(centre_of_bar_in_x_axis, freq_counts_S, color="#0101DF",
                                            alpha=0.5)
        # other colours that are compatible with colourblind readers: #8A084B Dark red, #B45F04 deep orange, reddish purple #4B088A
        # http://html-color-codes.info/
        # label the x-axis for each plot, based on the TMD
        ax.set_xlabel('average conservation ratio (membranous over nonmembranous)', fontsize=fontsize)
        # move the x-axis label closer to the x-axis
        ax.xaxis.set_label_coords(0.45, -0.085)
        xlim_min = s["mp_xlim_min01"]
        # take x-axis max from settings
        xlim_max = s["mp_xlim_max01"]
        # set x-axis min
        ax.set_xlim(xlim_min, xlim_max)
        # set x-axis ticks
        # use the slide selection to select every second item in the list as an xtick(axis label)
        ax.set_xticks([float('%0.1f' % c) for c in centre_of_bar_in_x_axis[::3]])
        ax.set_ylabel('freq', rotation='vertical', fontsize=fontsize)
        # change axis font size
        ax.tick_params(labelsize=fontsize)
        # create legend?#http://stackoverflow.com/questions/9834452/how-do-i-make-a-single-legend-for-many-subplots-with-matplotlib
        legend_obj = ax.legend(['AASMON (identity + similarity)', 'AAIMON (identity)', 'AAIMON norm (identity)'], loc='upper right',
                               fontsize=fontsize)
        # add figure number to top left of subplot
        ax.annotate(s=str(Fig_Nr) + '.', xy=(0.04, 0.9), fontsize=fontsize, xytext=None, xycoords='axes fraction',
                    alpha=0.75)
        # add figure title to top left of subplot
        ax.annotate(s=title, xy=(0.1, 0.9), fontsize=fontsize, xytext=None, xycoords='axes fraction', alpha=0.75)
        # # FROM RIMMA SCRIPT - not necessary
        # ax.yaxis.grid(True, zorder=0, linestyle=":", color="grey")
        # ax
        # for tic in ax.xaxis.get_major_ticks():
        #     tic.tick1On = False
        # for tic in ax.yaxis.get_major_ticks():
        #     tic.tick1On = False
        # ax.spines['top'].set_visible(False)
        # ax.spines['right'].set_visible(False)
        # # END FROM RIMMA SCRIPT

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)

    if s['Fig02_Density_AAIMON_vs_evol_dist']:
        Fig_Nr = 2
        Fig_name = 'List{:02d}_Fig02_Density_AAIMON_vs_evol_dist'.format(list_number)

        # read data from disk
        in_zipfile = pathdict["save_df_characterising_each_homol_TMD"]
        if os.path.isfile(in_zipfile):
            with zipfile.ZipFile(in_zipfile, "r", zipfile.ZIP_DEFLATED) as openzip:
                data = pickle.load(openzip.open("data_characterising_each_homol_TMD.pickle", "r"))
                binned_data = pickle.load(openzip.open("binned_data_characterising_each_homol_TMD.pickle", "r"))
        else:
            raise FileNotFoundError("{} not found".format(in_zipfile))

        vmax = s['vmax']

        fig, ax = plt.subplots(figsize=(5, 5))

        x = data[:, 0]  # FASTA_gapped_identity
        y = data[:, 1]  # AAIMON for each TMD

        # histogram definition
        # data range
        xyrange = [[0, max_evol_distance], [0, 3]]
        # number of bins
        bins = [max_evol_distance*2, 120]
        # density threshold
        thresh = 1

        # histogram the data
        hh, locx, locy = scipy.histogram2d(x, y, range=xyrange, bins=bins)

        # fill the areas with low density by NaNs
        hh[hh < thresh] = np.nan

        # ax.scatter(x=x, y=y, color="#EE762C", alpha=0.2, s=0.008, marker='x', linewidths=0.003)

        im = ax.imshow(np.flipud(hh.T), cmap='Oranges', extent=np.array(xyrange).flatten(),
                       interpolation='none', origin='upper', aspect='auto', vmin=0, vmax=vmax)

        ax.plot(binned_data[:, 0], binned_data[:, 1], color='#0F3750', label='non-normalised')
        ax.plot(binned_data[:, 0], binned_data[:, 2], color='#9ECEEC', label='normalised')
        # ax.grid(False, which='both')
        ax.tick_params(axis='both', which='major', length=3, width=1, color='#CCCCCC')
        ax.set_xlabel('evolutionary distance (% substitutions)', fontsize=fontsize)
        ax.set_ylabel('TM/nonTM conservation', rotation=90, fontsize=fontsize)

        # get colorbar from latest imshow element (color scale should be the same for all subplots)
        # fig.subplots_adjust(right=0.8)
        cbar_ax = fig.add_axes([0.12, 0.89, 0.78, 0.02])
        fig.colorbar(im, cax=cbar_ax, orientation='horizontal')
        cbar_ax.xaxis.set_ticks_position('top')
        labels = cbar_ax.get_xmajorticklabels()
        labels[-1] = '>{}    '.format(vmax)
        cbar_ax.set_xticklabels(labels)
        cbar_ax.tick_params(pad=0, labelsize=fontsize)
        ax.tick_params(pad=1, labelsize=fontsize)
        ax.legend(frameon=True, loc='upper left', fontsize=fontsize)

        # set the xlim based on the chosen settings for evolutionary distance of those homologues
        ax.set_xlim(min_evol_distance, max_evol_distance)

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)


    def Fig03_Density_lipo_vs_TM_conservation(df, letter, suffix, col_list_AAIMON_slope, col_list_lipo, max_evol_distance, base_filepath, save_png, save_pdf, dpi, fontsize):
        Fig_name = 'List{:02d}_Fig03{}_Density_lipo_vs_TM_conservation{}'.format(list_number, letter, suffix)
        title = suffix[1:]
        '''
        data array columns:
        |   0   |   1  |
        | Slope | lipo |
        '''
        data = np.empty([0, 2])
        sys.stdout.write('Fig03 collecting data: ')
        sys.stdout.flush()

        # for n, acc in enumerate(df.index[0:20]):
        #     list_of_TMDs = df.loc[acc, 'list_of_TMDs']
        #     if n % 200 == 0:
        #         sys.stdout.write('. ')
        #         sys.stdout.flush()
        #     for TMD in list_of_TMDs:
        #         add = np.array([df.loc[acc, '%s_AAIMON_slope' % TMD], df.loc[acc, '%s_lipo' % TMD]])
        #         data = (np.vstack((data, add)))
        # sys.stdout.write('\n')
        # data = data[~np.isnan(data).any(axis=1)]
        #


        # aaa(df)
        #
        # for n, acc in enumerate(df.index[0:20]):
        #     list_of_TMDs = df.loc[acc, 'list_of_TMDs']
        #     if n % 200 == 0:
        #         sys.stdout.write('. ')
        #         sys.stdout.flush()
        #     for TMD in list_of_TMDs:
        #         add = np.array([df.loc[acc, '%s_AAIMON_slope' % TMD], df.loc[acc, '%s_lipo' % TMD]])
        #         data = (np.vstack((data, add)))
        # sys.stdout.write('\n')
        # data = data[~np.isnan(data).any(axis=1)]
        #

        # add the signal peptide if necessary
        if "SP01_start" in df.columns:
            col_list_AAIMON_slope = ["SP01_AAIMON_slope"] + col_list_AAIMON_slope
            col_list_lipo = ["SP01_lipo"] + col_list_lipo
        # select all AAIMON slopes or lipo data
        df_slopes = df.loc[:, col_list_AAIMON_slope]
        df_lipos = df.loc[:, col_list_lipo]
        # check that .stack drops nans, and that there were exactly equal number of nans in the lipo and slope datasets
        if df_slopes.stack().shape != df_lipos.stack().shape:
            raise ValueError("There must be a nan in the lipo or AAIMON slopes. Check code, revert to orig if necessary.")

        # convert slopes and lipos to a 1D numpy array
        slopes = df_slopes.stack().values*1000
        lipos = df_lipos.stack().values
        # # join to a single numpy array
        # data = np.array([slopes, lipos]).T

        fig, (cbar_ax, ax) = plt.subplots(2, 1, figsize=(5, 5.5), gridspec_kw={'height_ratios': [0.2, 12]})
        #fontsize = 16
        # number of bins
        n_bins_x = int(max_evol_distance*2)
        n_bins_y = 120
        bins = [n_bins_x, n_bins_y]
        # density threshold
        thresh = 1

        # # plot AAIMON_slope data
        # x = data[:, 1]
        # y = data[:, 0] * 1000
        #


        x_border = 1.5
        y_border = 30
        xyrange = [[-x_border, x_border], [-y_border, y_border]]

        # histogram the data
        hh, locx, locy = scipy.histogram2d(lipos, slopes, range=xyrange, bins=bins)
        hh1 = hh.reshape(1, n_bins_x * n_bins_y)
        hh1 = hh1[hh1 > 0]
        vmax = np.percentile(hh1, 99)
        if vmax % 2 == True:
            vmax = vmax - 1
        # fill the areas with low density by NaNs
        hh[hh < thresh] = np.nan
        im = ax.imshow(np.flipud(hh.T), cmap='Oranges', extent=np.array(xyrange).flatten(),
                       interpolation='none', origin='upper', aspect='auto', vmin=0, vmax=vmax)

        cbar = matplotlib.colorbar.ColorbarBase(cbar_ax, cmap='Oranges', orientation='horizontal')
        if vmax < 10:
            cbar.set_ticks(np.linspace(0, 1, vmax + 1))
            labels = list(range(0, int(vmax), 1))
        else:
            cbar.set_ticks(np.linspace(0, 1, vmax / 2 + 1))
            labels = list(range(0, int(vmax), 2))

        labels.append('>{}'.format(int(vmax)))
        cbar.set_ticklabels(labels)
        cbar_ax.xaxis.set_ticks_position('top')

        ax.set_title(title, fontsize=fontsize)
        ax.set_xlabel('lipophilicity (Hessa scale)', fontsize=fontsize)
        ax.set_ylabel(r'm$_{\rm TM/nonTM} *10^{\rm -3}$', fontsize=fontsize)
        ax.tick_params(labelsize=fontsize, pad=3)
        cbar_ax.tick_params(labelsize=fontsize, pad=0)

        plt.subplots_adjust(hspace=0.03)
        plt.tight_layout()

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)

    if s['Fig03_Density_lipo_vs_TM_conservation']:
        Fig_Nr = 3

        # get the maximum mnumber of TMDs in the full dataset (e.g. 32)
        max_n_TMDs = int(df.number_of_TMDs_excl_SP.max())
        # create a large list of columns, e.g. ['TM01_AAIMON_slope',  'TM02_AAIMON_slope',  'TM03_AAIMON_slope', ...
        col_list_AAIMON_slope = ['TM{:02d}_AAIMON_slope'.format(TM_nr) for TM_nr in range(1, max_n_TMDs + 1)]
        col_list_lipo = ['TM{:02d}_lipo'.format(TM_nr) for TM_nr in range(1, max_n_TMDs + 1)]

        for i, prot_family in enumerate(list_prot_families):
            # a, b, c, etc
            letter = letters[i]
            # _GPCR, _nonGPCR, etc
            suffix = "_{}".format(prot_family[3:])
            # get appropriate dataframe subset for analysis (above)
            df_Fig03 = prot_family_df_dict[prot_family]
            # plot
            Fig03_Density_lipo_vs_TM_conservation(df_Fig03, letter, suffix, col_list_AAIMON_slope, col_list_lipo, max_evol_distance, base_filepath, save_png, save_pdf, dpi, fontsize)

        # for human multipass, test GPCR TM01 and TM07 only
        if list_number in [2,5]:
            # redefine as only the first and 7th TM (first and lost GPCR TM)
            col_list_AAIMON_slope = ['TM01_AAIMON_slope', 'TM07_AAIMON_slope']
            col_list_lipo = ['TM01_lipo', 'TM07_lipo']
            for i, prot_family in enumerate(list_prot_families):
                letter = letters[i]
                suffix = "_{}".format(prot_family[3:]) + "_TM01_and_TM07_only"
                df_Fig03 = prot_family_df_dict[prot_family]
                Fig03_Density_lipo_vs_TM_conservation(df_Fig03, letter, suffix, col_list_AAIMON_slope, col_list_lipo, max_evol_distance, base_filepath, save_png, save_pdf, dpi, fontsize)

    if s['Fig04_Boxplot_AAIMON_each_TMD']:
        Fig_Nr = 4
        title = 'Boxplot of all TMDs'
        Fig_name = 'List{:02d}_Fig04_Boxplot_AAIMON_each_TMD'.format(list_number)
        fig, ax = plt.subplots()
        # "#0489B1"
        alpha = 0.25
        col_width_value = 0.95
        ylabel = 'freq'
        xlabel = 'average conservation ratio (membranous over nonmembranous)'
        # legend =

        number_of_TMDs_excl_SP = df.number_of_TMDs_excl_SP.max()
        legend = []
        data_to_plot = []
        for i in range(1, number_of_TMDs_excl_SP.astype(np.int64) + 1):
            TM = 'TM%02d' % i
            hist_data_AAIMON_each_TM = df['TM%02d_AAIMON_mean' % i].dropna()
            if len(hist_data_AAIMON_each_TM) > 0:
                data_to_plot.append(hist_data_AAIMON_each_TM)
                legend.append(TM)

        meanpointprops = dict(marker='o', markerfacecolor='black', markersize=2)  # markeredgecolor='0.75',

        flierprops = dict(marker='o', markerfacecolor='green', markersize=12,
                          linestyle='none')
        boxplotcontainer = ax.boxplot(data_to_plot, sym='+', whis=1.5, showmeans=True,
                                                         meanprops=meanpointprops)
        ax.tick_params(labelsize=fontsize)
        for box in boxplotcontainer['boxes']:
            # change outline color
            box.set(color='black', linewidth=0.4)  # '7570b3'
            # change fill color
            # box.set( facecolor = '#1b9e77' )
            box.set_linewidth(0.4)

        ## change color and linewidth of the whiskers
        for whisker in boxplotcontainer['whiskers']:
            whisker.set(color='black', linewidth=0.4, dashes=(1, 1))

        ## change color and linewidth of the caps
        for cap in boxplotcontainer['caps']:
            cap.set(color='black', linewidth=0.4)

        ## change color and linewidth of the medians
        for median in boxplotcontainer['medians']:
            median.set(color='black', linewidth=0.4)

        # change the style of fliers and their fill
        for flier in boxplotcontainer['fliers']:
            flier.set(marker='o', color='0.8', alpha=0.1, markerfacecolor='0.3', markersize=3)

        ax.set_ylabel('AAIMON', rotation='vertical', fontsize=fontsize)

        ## Remove top axes and right axes ticks
        ax.get_xaxis().tick_bottom()
        ax.get_yaxis().tick_left()
        ## Custom x-axis labels
        ax.set_xticklabels(legend, rotation=45)
        # add figure number to top left of subplot
        ax.annotate(s=str(Fig_Nr) + '.', xy=(0.04, 0.9), fontsize=fontsize, xytext=None,
                                       xycoords='axes fraction', alpha=0.75)
        # add figure title to top left of subplot
        ax.annotate(s=title, xy=(0.1, 0.9), fontsize=fontsize, xytext=None, xycoords='axes fraction',
                                       alpha=0.75)

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)

    if s['Fig05_Boxplot_lipo_each_TMDs']:
        Fig_Nr = 5
        title = 'Boxplot lipophilicity of all TMDs'
        Fig_name = 'List{:02d}_Fig05_Boxplot_lipo_each_TMDs'.format(list_number)

        ### boxplot of all TMDs

        ### this section specifies the last bin to avoid bins containing only one TMD
        # join all numbers of TMDs together into a large list
        nested_list_all_TMDs = list(df['number_of_TMDs_excl_SP'])
        # convert list to pandas series
        all_TMDs_series = pd.Series(nested_list_all_TMDs)
        # obtain series of TMD_counts
        TMD_counts = all_TMDs_series.value_counts()
        # exclude TMD numbers with less than x applicable proteins from boxplot max detection
        boxplot_cutoff_number_of_TMDs = 20
        TMD_counts_major = TMD_counts[TMD_counts >= boxplot_cutoff_number_of_TMDs]
        max_num_TMDs = int(TMD_counts_major.index.max())

        if pd.notnull(max_num_TMDs):
            # title = str(keyword) + '_Boxplot'
            # Fig_name = str(str(Fig_Nr) + '._' + 'Keyword_' + title)
            fig, ax = plt.subplots()
            ax2 = plt.twinx()

            legend = []
            data_to_plot = []
            for i in range(1, max_num_TMDs + 1):
                TM = 'TM%02d' % i
                hist_data_AAIMON_each_TM = df['TM%02d_lipo' % i].dropna()
                if len(hist_data_AAIMON_each_TM) > 0:
                    data_to_plot.append(hist_data_AAIMON_each_TM)
                    legend.append(TM)

            # add values of every TMD number that is larger than the boxplot_cutoff_number_of_TMDs to final bin
            data_for_final_bin = []
            for i in range(max_num_TMDs + 1, df.number_of_TMDs_excl_SP.max().astype('int') + 1):
                # TM_final = 'TM%02d' % i
                hist_data_AAIMON_each_TM_final_bin = df['TM%02d_lipo' % i].dropna()
                # if len(hist_data_AAIMON_each_TM) > 0:
                data_for_final_bin.append(hist_data_AAIMON_each_TM_final_bin)
            final_bin = list(itertools.chain.from_iterable(data_for_final_bin))
            data_to_plot.append(final_bin)
            legend.append('>{}'.format(TM))

            n_elements_in_bin = []
            for element in data_to_plot:
                n_elements_in_bin.append(len(element))

            x = range(1, len(legend) + 1)
            ax2.plot(x, n_elements_in_bin, color='#0076B8', alpha=0.5)
            ax2.grid(b=False)
            ax2.set_ylabel('number of TMDs in bin', rotation='vertical', fontsize=fontsize)
            ax2.tick_params(labelsize=fontsize)

            meanpointprops = dict(marker='o', markerfacecolor='black', markersize=2, markeredgecolor='black')  # markeredgecolor='0.75',

            flierprops = dict(marker='o', markerfacecolor='green', markersize=12,
                              linestyle='none')
            # plot boxplot
            boxplotcontainer = ax.boxplot(data_to_plot, sym='+', whis=1.5, showmeans=True,
                                          meanprops=meanpointprops)
            ax.tick_params(labelsize=fontsize)
            for box in boxplotcontainer['boxes']:
                # change outline color
                box.set(color='black', linewidth=0.4)  # '7570b3'
                # change fill color
                # box.set( facecolor = '#1b9e77' )
                box.set_linewidth(0.4)

            ## change color and linewidth of the whiskers
            for whisker in boxplotcontainer['whiskers']:
                whisker.set(color='black', linewidth=0.4, dashes=(1, 1))

            ## change color and linewidth of the caps
            for cap in boxplotcontainer['caps']:
                cap.set(color='black', linewidth=0.4)

            ## change color and linewidth of the medians
            for median in boxplotcontainer['medians']:
                median.set(color='black', linewidth=0.4)

            # change the style of fliers and their fill
            for flier in boxplotcontainer['fliers']:
                flier.set(marker='o', color='0.8', alpha=0.1, markerfacecolor='0.3', markersize=3)

            ax.set_ylabel('lipophilicity (Hessa scale)', rotation='vertical', fontsize=fontsize)
            # ax.set_ylim(-20, 30)

            ## Remove top axes and right axes ticks
            ax.get_xaxis().tick_bottom()
            ax.get_yaxis().tick_left()
            ## Custom x-axis labels
            ax.set_xticklabels(legend, rotation=45)
            ax.set_ylim(-0.5, 1)

            # add figure number to top left of subplot
            ax.annotate(s=str(Fig_Nr) + '.', xy=(0.04, 0.9), fontsize=fontsize, xytext=None,
                        xycoords='axes fraction', alpha=0.75)
            # add figure title to top left of subplot
            ax.annotate(s=title, xy=(0.1, 0.9), fontsize=fontsize, xytext=None, xycoords='axes fraction',
                        alpha=0.75)

            utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)


    if s['Fig06_Boxplot_AAIMON_by_number_of_TMDs']:
        Fig_Nr = 6
        title = 'num_TMDs vs AAIMON'
        Fig_name = 'List{:02d}_Fig06_Boxplot_AAIMON_by_number_of_TMDs'.format(list_number)
        fig, ax = plt.subplots()

        alpha = 0.25
        col_width_value = 0.95
        legend = []
        data_to_plot = []
        # iterate through df and get all AAIMONs with specified number of TMD
        for i in range(1, max_num_TMDs + 1):
            hist_data = []
            for acc in df.loc[df['list_of_TMDs'].notnull()].loc[df['list_of_TMDs'] != 'nan'].index:
                if df.loc[acc, 'number_of_TMDs'] == i:
                    hist_data.append(df.loc[acc, 'AAIMON_mean_all_TMDs'])
            data_to_plot.append(hist_data)
            legend.append(i)
        meanpointprops = dict(marker='o', markerfacecolor='black', markersize=3)  # markeredgecolor='0.75',
        flierprops = dict(marker='o', markerfacecolor='green', markersize=12,
                          linestyle='none')
        boxplotcontainer = ax.boxplot(data_to_plot, sym='+', whis=1.5, showmeans=True,
                                      meanprops=meanpointprops)
        ax.tick_params(labelsize=fontsize)
        for box in boxplotcontainer['boxes']:
            # change outline color
            box.set(color='black', linewidth=0.4)  # '7570b3'
            # change fill color
            # box.set( facecolor = '#1b9e77' )
            box.set_linewidth(0.4)

        ## change color and linewidth of the whiskers
        for whisker in boxplotcontainer['whiskers']:
            whisker.set(color='black', linewidth=0.4, dashes=(1, 1))

        ## change color and linewidth of the caps
        for cap in boxplotcontainer['caps']:
            cap.set(color='black', linewidth=0.4)

        ## change color and linewidth of the medians
        for median in boxplotcontainer['medians']:
            median.set(color='black', linewidth=0.4)

        # change the style of fliers and their fill
        for flier in boxplotcontainer['fliers']:
            flier.set(marker='o', color='0.8', alpha=0.1, markerfacecolor='0.3', markersize=3)

        ax.set_xlabel('number of TMDs in protein', fontsize=fontsize)
        # move the x-axis label closer to the x-axis
        ax.xaxis.set_label_coords(0.45, -0.085)
        ax.set_ylabel('Average TM/nonTM conservation for all TMDs', fontsize=fontsize)
        # Remove top axes and right axes ticks
        ax.get_xaxis().tick_bottom()
        ax.get_yaxis().tick_left()
        # Custom x-axis labels
        ax.set_xticklabels(legend)
        # add figure number to top left of subplot
        ax.annotate(s=str(Fig_Nr) + '.', xy=(0.04, 0.9), fontsize=fontsize, xytext=None,
                    xycoords='axes fraction', alpha=0.75)
        # add figure title to top left of subplot
        ax.annotate(s=title, xy=(0.1, 0.9), fontsize=fontsize, xytext=None, xycoords='axes fraction',
                    alpha=0.75)

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)


    if s['Fig07_Density_AAIMON_or_slope_vs_evol_distance']:
        Fig_Nr = 7
        title = 'compare AAIMON with AAIMON_slope'
        Fig_name = 'List{:02d}_Fig07_Density_AAIMON_or_slope_vs_evol_distance'.format(list_number)

        vmax = 3
        fig, (ax1, ax2) = plt.subplots(2, sharex=True, sharey=False, figsize=(5, 10))

        # histogram definition
        # data range
        xyrange = [[0, max_evol_distance], [0.2, 1.8]]
        # number of bins
        bins = [max_evol_distance*2, 120]
        # density threshold
        thresh = 1

        # plot AAIMON data
        x = df.obs_changes_mean
        y = df.AAIMON_mean_all_TMDs
        # histogram the data
        hh, locx, locy = scipy.histogram2d(x, y, range=xyrange, bins=bins)
        # fill the areas with low density by NaNs
        hh[hh < thresh] = np.nan
        im = ax1.imshow(np.flipud(hh.T), cmap='Oranges', extent=np.array(xyrange).flatten(),
                        interpolation='none', origin='upper', aspect='auto', vmin=0, vmax=vmax)

        # plot AAIMON_slope data with changed xyrange
        xyrange = [[0, max_evol_distance], [-20, 20]]
        # plot AAIMON_slope data
        x = df.obs_changes_mean
        y = df.AAIMON_slope_mean_all_TMDs * 1000
        # histogram the data
        hh, locx, locy = scipy.histogram2d(x, y, range=xyrange, bins=bins)
        # fill the areas with low density by NaNs
        hh[hh < thresh] = np.nan
        im = ax2.imshow(np.flipud(hh.T), cmap='Oranges', extent=np.array(xyrange).flatten(),
                        interpolation='none', origin='upper', aspect='auto', vmin=0, vmax=vmax)

        # define axis limits and parameters, set labels
        ax1.set_ylim(0.2, 1.8)
        ax2.set_ylim(-20, 20)
        ax1.tick_params(labelsize=fontsize, pad=2)
        ax2.tick_params(labelsize=fontsize, pad=2)
        ax1.set_ylabel('TM/nonTM conservation', fontsize=fontsize)
        ax2.set_ylabel(r'm$_{\rm TM/nonTM} *10^{\rm -3}$', fontsize=fontsize)
        ax1.set(adjustable='box-forced')
        ax2.set(adjustable='box-forced')
        plt.xlabel('average evolutionary distance of homologues (% substitutions)', fontsize=fontsize)

        # add colorbar
        cbar_ax = fig.add_axes([0.12, 0.89, 0.78, 0.01])
        fig.colorbar(im, cax=cbar_ax, orientation='horizontal')
        cbar_ax.xaxis.set_ticks_position('top')
        labels = cbar_ax.get_xmajorticklabels()
        labels[-1] = '>{}'.format(vmax)
        cbar_ax.set_xticklabels(labels)
        cbar_ax.tick_params(pad=0, labelsize=fontsize)
        # remove white space between subplots
        fig.subplots_adjust(wspace=0.2, hspace=0.075)

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)

    if s['Fig08_Hist_AAIMON_slope_TM01_vs_lastTM']:
        ###### for backwards compatibility ##### can be removed if all data is re-processed after march 5 2017
        if not 'AAIMON_slope_last_TMD' in df.columns:
            sys.stdout.write('AAIMON_slope_last_TMD not in dataframe -> older version of data, re-run "gather_AAIMON_ratios"; adding data for figure')
            for n, acc in enumerate(df.index):
                if n % 200 == 0:
                    sys.stdout.write('. '), sys.stdout.flush()
                last_TMD = df.loc[acc, 'last_TMD']
                df.loc[acc, 'AAIMON_slope_last_TMD'] = df.loc[acc, '%s_AAIMON_slope' % last_TMD]

        Fig_Nr = 8
        title = 'AAIMON_slope TM01 vs lastTM'
        Fig_name = 'List{:02d}_Fig08_Hist_AAIMON_slope_TM01_vs_lastTM'.format(list_number)
        binlist = np.linspace(-40, 40, 61)
        linewidth = 1
        fig, ax = plt.subplots()

        ###   TM01 AAIMON_slope   ###
        # create numpy array of membranous over nonmembranous conservation ratios (identity)
        hist_data = (df['TM01_AAIMON_slope'] * 1000).dropna()
        # use numpy to create a histogram
        freq_counts, bin_array = np.histogram(hist_data, bins=binlist)
        freq_counts_normalised = freq_counts / freq_counts.max()
        # assuming all of the bins are exactly the same size, make the width of the column equal to XX% (e.g. 95%) of each bin
        col_width = float('%0.3f' % (0.95 * (bin_array[1] - bin_array[0])))
        # when align='center', the central point of the bar in the x-axis is simply the middle of the bins ((bin_0-bin_1)/2, etc)
        centre_of_bar_in_x_axis = (bin_array[:-2] + bin_array[1:-1]) / 2
        # add the final bin, which is physically located just after the last regular bin but represents all higher values
        bar_width = centre_of_bar_in_x_axis[3] - centre_of_bar_in_x_axis[2]
        centre_of_bar_in_x_axis = np.append(centre_of_bar_in_x_axis, centre_of_bar_in_x_axis[-1] + bar_width)
        linecontainer_AAIMON_mean = ax.plot(centre_of_bar_in_x_axis, freq_counts_normalised, color='k',
                                            alpha=0.9, linewidth=linewidth)

        ###   last TMD AAIMON_slope   ###
        # create numpy array of membranous over nonmembranous conservation ratios (identity)
        hist_data = (df['AAIMON_slope_last_TMD'] * 1000).dropna()
        # use numpy to create a histogram
        freq_counts, bin_array = np.histogram(hist_data, bins=binlist)
        freq_counts_normalised = freq_counts / freq_counts.max()
        # assuming all of the bins are exactly the same size, make the width of the column equal to XX% (e.g. 95%) of each bin
        col_width = float('%0.3f' % (0.95 * (bin_array[1] - bin_array[0])))
        # when align='center', the central point of the bar in the x-axis is simply the middle of the bins ((bin_0-bin_1)/2, etc)
        centre_of_bar_in_x_axis = (bin_array[:-2] + bin_array[1:-1]) / 2
        # add the final bin, which is physically located just after the last regular bin but represents all higher values
        bar_width = centre_of_bar_in_x_axis[3] - centre_of_bar_in_x_axis[2]
        centre_of_bar_in_x_axis = np.append(centre_of_bar_in_x_axis, centre_of_bar_in_x_axis[-1] + bar_width)
        linecontainer_AAIMON_mean = ax.plot(centre_of_bar_in_x_axis, freq_counts_normalised, ':', color='k',
                                            alpha=0.9,
                                            linewidth=linewidth)

        ax.set_xlabel(r'm$_{\rm TM/nonTM} *10^{\rm -3}$', fontsize=fontsize)
        # move the x-axis label closer to the x-axis
        ax.xaxis.set_label_coords(0.5, -0.085)
        # x and y axes min and max
        xlim_min = -30
        xlim_max = 30
        ax.set_xlim(xlim_min, xlim_max)
        ax.set_ylabel('freq', rotation='vertical', fontsize=fontsize)
        # change axis font size
        ax.tick_params(labelsize=fontsize)
        # create legend
        ax.xaxis.set_label_coords(0.5, -0.07)
        # ax.yaxis.set_label_coords(-0.005, 0.5)

        # add legend
        ax.legend(['TM01', 'last TM'], fontsize=fontsize, frameon=True)

        # add annotations
        ax.annotate(s="TM less conserved", xy=(0, -0.09), fontsize=fontsize, xytext=None, xycoords='axes fraction')
        ax.annotate(s="TM more conserved", xy=(1.0, -0.09), fontsize=fontsize, xytext=None, horizontalalignment='right', xycoords='axes fraction')

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)

    if s['Fig09_Hist_lipo_TM01_vs_lastTM']:
        Fig_Nr = 9
        title = 'Lipo TM01 vs lastTM'
        Fig_name = 'List{:02d}_Fig09_Hist_lipo_TM01_vs_lastTM'.format(list_number)
        min_ = -0.5
        max_ = 0.8
        binlist = np.linspace(min_, max_, 21)
        fig, ax = plt.subplots()
        # offset = len(protein_lists) - 1

        # create numpy array of membranous over nonmembranous conservation ratios (identity)
        hist_data = np.array(df['lipo_mean_excl_TM01'].dropna())
        # use numpy to create a histogram
        freq_counts, bin_array = np.histogram(hist_data, bins=binlist)
        freq_counts_normalised = freq_counts / freq_counts.max()
        # assuming all of the bins are exactly the same size, make the width of the column equal to XX% (e.g. 95%) of each bin
        col_width = float('%0.3f' % (0.95 * (bin_array[1] - bin_array[0])))
        # when align='center', the central point of the bar in the x-axis is simply the middle of the bins ((bin_0-bin_1)/2, etc)
        centre_of_bar_in_x_axis = (bin_array[:-2] + bin_array[1:-1]) / 2
        # add the final bin, which is physically located just after the last regular bin but represents all higher values
        bar_width = centre_of_bar_in_x_axis[3] - centre_of_bar_in_x_axis[2]
        centre_of_bar_in_x_axis = np.append(centre_of_bar_in_x_axis, centre_of_bar_in_x_axis[-1] + bar_width)
        linecontainer_AAIMON_mean = ax.plot(centre_of_bar_in_x_axis, freq_counts_normalised, color=color_list_TUM_blue[0],
                                            alpha=1,
                                            linewidth=1)

        # create numpy array of membranous over nonmembranous conservation ratios (identity)
        hist_data = np.array(df['TM01_lipo'].dropna())
        # use numpy to create a histogram
        freq_counts, bin_array = np.histogram(hist_data, bins=binlist)
        freq_counts_normalised = freq_counts / freq_counts.max()
        # assuming all of the bins are exactly the same size, make the width of the column equal to XX% (e.g. 95%) of each bin
        col_width = float('%0.3f' % (0.95 * (bin_array[1] - bin_array[0])))
        # when align='center', the central point of the bar in the x-axis is simply the middle of the bins ((bin_0-bin_1)/2, etc)
        centre_of_bar_in_x_axis = (bin_array[:-2] + bin_array[1:-1]) / 2
        # add the final bin, which is physically located just after the last regular bin but represents all higher values
        bar_width = centre_of_bar_in_x_axis[3] - centre_of_bar_in_x_axis[2]
        centre_of_bar_in_x_axis = np.append(centre_of_bar_in_x_axis, centre_of_bar_in_x_axis[-1] + bar_width)
        linecontainer_AAIMON_mean = ax.plot(centre_of_bar_in_x_axis, freq_counts_normalised, color=color_list_TUM_blue[1],
                                            alpha=1, linewidth=1)

        # # create numpy array of membranous over nonmembranous conservation ratios (identity)
        # hist_data = np.array(df['lipo_last_TMD'].dropna())
        # # use numpy to create a histogram
        # freq_counts, bin_array = np.histogram(hist_data, bins=binlist)
        # freq_counts_normalised = freq_counts / freq_counts.max()
        # # assuming all of the bins are exactly the same size, make the width of the column equal to XX% (e.g. 95%) of each bin
        # col_width = float('%0.3f' % (0.95 * (bin_array[1] - bin_array[0])))
        # # when align='center', the central point of the bar in the x-axis is simply the middle of the bins ((bin_0-bin_1)/2, etc)
        # centre_of_bar_in_x_axis = (bin_array[:-2] + bin_array[1:-1]) / 2
        # # add the final bin, which is physically located just after the last regular bin but represents all higher values
        # bar_width = centre_of_bar_in_x_axis[3] - centre_of_bar_in_x_axis[2]
        # centre_of_bar_in_x_axis = np.append(centre_of_bar_in_x_axis, centre_of_bar_in_x_axis[-1] + bar_width)
        # linecontainer_AAIMON_mean = ax.plot(centre_of_bar_in_x_axis, freq_counts_normalised, color=color_list_TUM_blue[2],
        #                                     alpha=1,
        #                                     linewidth=1)

        ###############################################################
        #                                                             #
        #                       set up plot style                     #
        #                                                             #
        ###############################################################

        ax.set_xlabel('lipophilicity (Hessa scale)', fontsize=fontsize)
        # move the x-axis label closer to the x-axis
        ax.xaxis.set_label_coords(0.5, -0.085)
        # x axes min and max
        xlim_min = min_
        xlim_max = max_
        ax.set_xlim(xlim_min, xlim_max)
        ax.set_ylabel('freq', rotation='vertical', fontsize=fontsize)
        # change axis font size
        ax.tick_params(labelsize=fontsize)

        # add annotations
        ax.annotate(s="more lipophilic", xy=(0, -0.1), fontsize=fontsize, xytext=None, xycoords='axes fraction')
        ax.annotate(s="less lipophilic", xy=(1.0, -0.1), fontsize=fontsize, xytext=None, horizontalalignment='right', xycoords='axes fraction')

        ax.legend(['mean excl. TM01', 'TM01'], fontsize=fontsize, frameon=True)

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)


    if s['Fig10_Boxplot_AAIMON_by_number_of_TMDs'] and s["max_TMDs"] >= 2:
        Fig_Nr = 10
        title = 'num_TMDs vs AAIMON'
        Fig_name = 'List{:02d}_Fig10_Boxplot_AAIMON_by_number_of_TMDs'.format(list_number)
        fig, ax = plt.subplots()

        # data that is binned
        column_for_bins = 'number_of_TMDs'
        # data that is plotted in bin
        column_for_data = 'AAIMON_mean_all_TMDs'
        hist_data = []
        legend = []
        TMD_number = list(range(1, 16, 1))
        for element in TMD_number:
            select = df[column_for_bins] == element
            data = df.loc[select, column_for_data].values
            hist_data.append(data)
            legend.append(element)
        select = df[column_for_bins] > TMD_number[-1]
        data = df.loc[select, column_for_data].values
        hist_data.append(data)
        legend.append('>15')

        fig, ax = plt.subplots()

        meanpointprops = dict(marker='o', markerfacecolor='black', markersize=3, markeredgecolor='black')

        flierprops = dict(marker='o', markerfacecolor='black', markersize=12, linestyle='none')
        boxplotcontainer = ax.boxplot(hist_data, sym='+', whis=1.5, showmeans=True,
                                      meanprops=meanpointprops)

        list_n_datapoints = [len(x) for x in hist_data]
        x_for_list_n_datapoints = list(range(1, len(list_n_datapoints) + 1, 1))
        ax2 = ax.twinx()
        line_graph_container = ax2.plot(x_for_list_n_datapoints, list_n_datapoints, color="#53A7D5", alpha=0.8)

        for box in boxplotcontainer['boxes']:
            # change outline color
            box.set(color='black', linewidth=0.4)  # '7570b3'
            # change fill color
            # box.set( facecolor = '#1b9e77' )
            box.set_linewidth(0.4)

        # change color and linewidth of the whiskers
        for whisker in boxplotcontainer['whiskers']:
            whisker.set(color='black', linewidth=0.4, dashes=(1, 1))

        # change color and linewidth of the caps
        for cap in boxplotcontainer['caps']:
            cap.set(color='black', linewidth=0.4)

        # change color and linewidth of the medians
        for median in boxplotcontainer['medians']:
            median.set(color='black', linewidth=0.4)

        # change the style of fliers and their fill
        for flier in boxplotcontainer['fliers']:
            flier.set(marker='o', color='0.8', alpha=0.1, markerfacecolor='0.3', markersize=3)

        ax.set_xlabel('number of TMDs in protein', fontsize=fontsize)
        ax.tick_params(labelsize=fontsize)
        ax2.tick_params(labelsize=fontsize)
        ax.set_ylim(ymin=0, ymax=2)
        ax2.set_ylim(ymin=0, ymax=800)
        ax.set_xlim(xmin=0, xmax=17)
        # move the x-axis label closer to the x-axis
        # ax.xaxis.set_label_coords(0.45, -0.085)
        ax.set_ylabel('Average TM/nonTM conservation for all TMDs', fontsize=fontsize)
        ax2.set_ylabel('Number of proteins in bin', fontsize=fontsize)
        ## Remove top axes and right axes ticks
        ax.get_xaxis().tick_bottom()
        ax.get_yaxis().tick_left()
        ## Custom x-axis labels
        ax.set_xticklabels(legend)

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)

    if s['Fig11_Boxplot_AAIMON_by_seqlen']:
        Fig_Nr = 11
        title = 'seqlen vs AAIMON'
        Fig_name = 'List{:02d}_Fig11_Boxplot_AAIMON_by_seqlen'.format(list_number)

        fig, ax = plt.subplots()

        # data that is binned
        column_for_bins = 'seqlen'
        # data that is plotted in bin
        column_for_data = 'AAIMON_mean_all_TMDs'
        # specify variable for binning function
        x = df[column_for_bins]
        # specify number of bins
        nbin = 10
        npt = len(x)
        # get bin-borders
        borders = np.interp(np.linspace(0, npt, nbin + 1), np.arange(npt), np.sort(x)).astype(int).tolist()
        # extend the bin borders to catch up every value
        borders[0] = 0
        borders[-1] = borders[-1] + 1
        # initialise lists for legend and data in bin
        legend = []
        hist_data = []
        # generate data in bin via selecting rows from pandas dataframe, create legend
        for n in range(1, len(borders), 1):
            legend.append('-'.join([str(borders[n - 1]), str(borders[n])]))
            select = (df[column_for_bins] > borders[n - 1]) & (df[column_for_bins] <= borders[n])
            data = df.loc[select, column_for_data].values
            hist_data.append(data)

        meanpointprops = dict(marker='o', markerfacecolor='black', markersize=3)  # markeredgecolor='0.75',
        flierprops = dict(marker='o', markerfacecolor='green', markersize=12, linestyle='none')
        boxplotcontainer = ax.boxplot(hist_data, sym='+', whis=1.5, showmeans=True,
                                      meanprops=meanpointprops)

        ax.tick_params(labelsize=fontsize)
        for box in boxplotcontainer['boxes']:
            # change outline color
            box.set(color='black', linewidth=0.4)  # '7570b3'
            # change fill color
            # box.set( facecolor = '#1b9e77' )
            box.set_linewidth(0.4)

        # change color and linewidth of the whiskers
        for whisker in boxplotcontainer['whiskers']:
            whisker.set(color='black', linewidth=0.4, dashes=(1, 1))

        # change color and linewidth of the caps
        for cap in boxplotcontainer['caps']:
            cap.set(color='black', linewidth=0.4)

        # change color and linewidth of the medians
        for median in boxplotcontainer['medians']:
            median.set(color='black', linewidth=0.4)

        # change the style of fliers and their fill
        for flier in boxplotcontainer['fliers']:
            flier.set(marker='o', color='0.8', alpha=0.1, markerfacecolor='0.3', markersize=3)

        ax.set_xlabel('Length of protein in bins', fontsize=fontsize)
        ax.set_ylim(ymin=0, ymax=2)
        # move the x-axis label closer to the x-axis
        # ax.xaxis.set_label_coords(0.45, -0.085)
        ax.set_ylabel('Average TM/nonTM conservation for all TMDs', fontsize=fontsize)
        ## Remove top axes and right axes ticks
        ax.get_xaxis().tick_bottom()
        ax.get_yaxis().tick_left()
        ## Custom x-axis labels
        ax.set_xticklabels(legend, rotation=25)

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)

    if s['Fig12_Boxplot_AAIMON_by_nonTMD_coverage']:
        Fig_Nr = 12
        title = 'seqlen vs AAIMON'
        Fig_name = 'List{:02d}_Fig12_Boxplot_AAIMON_by_nonTMD_coverage'.format(list_number)

        fig, ax = plt.subplots()

        # data that is binned
        column_for_bins = 'nonTMD_SW_align_len_mean'
        # data that is plotted in bin
        column_for_data = 'AAIMON_mean_all_TMDs'
        # specify variable for binning function
        x = df[column_for_bins]
        # specify number of bins
        nbin = 10
        npt = len(x)
        # get bin-borders
        borders = np.interp(np.linspace(0, npt, nbin + 1), np.arange(npt), np.sort(x)).astype(int).tolist()
        # extend the bin borders to catch up every value
        borders[0] = 0
        borders[-1] = borders[-1] + 1
        # initialise lists for legend and data in bin
        legend = []
        hist_data = []
        # generate data in bin via selecting rows from pandas dataframe, create legend
        for n in range(1, len(borders), 1):
            legend.append('-'.join([str(borders[n - 1]), str(borders[n])]))
            select = (df[column_for_bins] > borders[n - 1]) & (df[column_for_bins] <= borders[n])
            data = df.loc[select, column_for_data].values
            hist_data.append(data)

        meanpointprops = dict(marker='o', markerfacecolor='black', markersize=3)  # markeredgecolor='0.75',

        flierprops = dict(marker='o', markerfacecolor='green', markersize=12, linestyle='none')
        boxplotcontainer = ax.boxplot(hist_data, sym='+', whis=1.5, showmeans=True,
                                      meanprops=meanpointprops)

        ax.tick_params(labelsize=fontsize)
        for box in boxplotcontainer['boxes']:
            # change outline color
            box.set(color='black', linewidth=0.4)  # '7570b3'
            # change fill color
            # box.set( facecolor = '#1b9e77' )
            box.set_linewidth(0.4)

        # change color and linewidth of the whiskers
        for whisker in boxplotcontainer['whiskers']:
            whisker.set(color='black', linewidth=0.4, dashes=(1, 1))

        # change color and linewidth of the caps
        for cap in boxplotcontainer['caps']:
            cap.set(color='black', linewidth=0.4)

        # change color and linewidth of the medians
        for median in boxplotcontainer['medians']:
            median.set(color='black', linewidth=0.4)

        # change the style of fliers and their fill
        for flier in boxplotcontainer['fliers']:
            flier.set(marker='o', color='0.8', alpha=0.1, markerfacecolor='0.3', markersize=3)

        ax.set_xlabel('Average length of nonTMD region in homologues', fontsize=fontsize)
        ax.set_ylim(ymin=0, ymax=2)
        # move the x-axis label closer to the x-axis
        # ax.xaxis.set_label_coords(0.45, -0.085)
        ax.set_ylabel('Average TM/nonTM conservation for all TMDs', fontsize=fontsize)
        ## Remove top axes and right axes ticks
        ax.get_xaxis().tick_bottom()
        ax.get_yaxis().tick_left()
        ## Custom x-axis labels
        ax.set_xticklabels(legend, rotation=25)

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)

    if s['Fig13_Boxplot_AAIMON_by_num_of_simap_hits']:
        Fig_Nr = 13
        title = 'number SIMAP hits'
        Fig_name = 'List{:02d}_Fig13_Boxplot_AAIMON_by_num_of_simap_hits'.format(list_number)

        fig, ax = plt.subplots()

        # data that is binned
        column_for_bins = 'AAIMON_n_homol'
        # data that is plotted in bin
        column_for_data = 'AAIMON_mean_all_TMDs'
        # specify variable for binning function
        x = df[column_for_bins]
        # specify number of bins
        nbin = 10
        npt = len(x)
        # get bin-borders
        borders = np.interp(np.linspace(0, npt, nbin + 1), np.arange(npt), np.sort(x)).astype(int).tolist()
        # extend the bin borders to catch up every value
        borders[0] = 0
        borders[-1] = borders[-1] + 1
        # initialise lists for legend and data in bin
        legend = []
        hist_data = []
        # generate data in bin via selecting rows from pandas dataframe, create legend
        for n in range(1, len(borders), 1):
            legend.append('-'.join([str(borders[n - 1]), str(borders[n])]))
            select = (df[column_for_bins] > borders[n - 1]) & (df[column_for_bins] <= borders[n])
            data = df.loc[select, column_for_data].values
            hist_data.append(data)

        meanpointprops = dict(marker='o', markerfacecolor='black', markersize=3)  # markeredgecolor='0.75',

        flierprops = dict(marker='o', markerfacecolor='green', markersize=12, linestyle='none')
        boxplotcontainer = ax.boxplot(hist_data, sym='+', whis=1.5, showmeans=True,
                                      meanprops=meanpointprops)

        ax.tick_params(labelsize=fontsize)
        for box in boxplotcontainer['boxes']:
            # change outline color
            box.set(color='black', linewidth=0.4)  # '7570b3'
            # change fill color
            # box.set( facecolor = '#1b9e77' )
            box.set_linewidth(0.4)

        # change color and linewidth of the whiskers
        for whisker in boxplotcontainer['whiskers']:
            whisker.set(color='black', linewidth=0.4, dashes=(1, 1))

        # change color and linewidth of the caps
        for cap in boxplotcontainer['caps']:
            cap.set(color='black', linewidth=0.4)

        # change color and linewidth of the medians
        for median in boxplotcontainer['medians']:
            median.set(color='black', linewidth=0.4)

        # change the style of fliers and their fill
        for flier in boxplotcontainer['fliers']:
            flier.set(marker='o', color='0.8', alpha=0.1, markerfacecolor='0.3', markersize=3)

        ax.set_xlabel('total number of homologues', fontsize=fontsize)
        ax.set_ylim(ymin=0, ymax=2)
        # move the x-axis label closer to the x-axis
        # ax.xaxis.set_label_coords(0.45, -0.085)
        ax.set_ylabel('Average TM/nonTM conservation for all TMDs', fontsize=fontsize)
        ## Remove top axes and right axes ticks
        ax.get_xaxis().tick_bottom()
        ax.get_yaxis().tick_left()
        ## Custom x-axis labels
        ax.set_xticklabels(legend, rotation=25)

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)

    if 'uniprot_KW' in df.columns:

        if s['Fig14_Hist_AAIMON_GPCRs_vs_nonGPCRs']:
            if True in df.GPCR:
                Fig_Nr = 14
                title = 'only GPCR in uniprot KW, NORM'
                Fig_name = 'List{:02d}_Fig14_Hist_AAIMON_GPCRs_vs_nonGPCRs'.format(list_number)
                fig, ax = plt.subplots()
                # create numpy array of membranous over nonmembranous conservation ratios (identity)
                hist_data_AAIMON_mean = np.array(df_GPCR['AAIMON_mean_all_TMDs'].dropna())
                # use numpy to create a histogram
                freq_counts_I, bin_array_I = np.histogram(hist_data_AAIMON_mean, bins=binlist)
                # normalize the frequency counts
                freq_counts_normalised = freq_counts_I / freq_counts_I.max()
                # assuming all of the bins are exactly the same size, make the width of the column equal to 70% of each bin
                col_width = float('%0.3f' % (0.95 * (bin_array_I[1] - bin_array_I[0])))
                # when align='center', the central point of the bar in the x-axis is simply the middle of the bins ((bin_0-bin_1)/2, etc)
                centre_of_bar_in_x_axis = (bin_array_I[:-2] + bin_array_I[1:-1]) / 2
                # add the final bin, which is physically located just after the last regular bin but represents all higher values
                bar_width = centre_of_bar_in_x_axis[3] - centre_of_bar_in_x_axis[2]
                centre_of_bar_in_x_axis = np.append(centre_of_bar_in_x_axis, centre_of_bar_in_x_axis[-1] + bar_width)
                barcontainer_AAIMON_mean = ax.bar(left=centre_of_bar_in_x_axis,
                                                  height=freq_counts_normalised,
                                                  align='center', width=col_width, color="#0489B1",
                                                  alpha=0.5, linewidth=0.1)  # edgecolor='black',
                # other colours that are compatible with colourblind readers: #8A084B Dark red, #B45F04 deep orange, reddish purple #4B088A
                # http://html-color-codes.info/
                # label the x-axis for each plot, based on the TMD
                ax.set_xlabel('average conservation ratio (membranous over nonmembranous)',
                              fontsize=fontsize)
                # move the x-axis label closer to the x-axis
                ax.xaxis.set_label_coords(0.45, -0.085)
                xlim_min = 0.8
                xlim_max = 1.5
                ax.set_xlim(xlim_min, xlim_max)
                # set x-axis ticks
                # use the slide selection to select every second item in the list as an xtick(axis label)
                ax.set_xticks([float('%0.1f' % c) for c in centre_of_bar_in_x_axis[::3]])
                ax.set_ylabel('freq', rotation='vertical', fontsize=fontsize)
                # change axis font size
                ax.tick_params(labelsize=fontsize)

                '''
                NON-GPCRS
                '''
                df_nonGPCR = df.loc[df['GPCR'] == False]

                # create numpy array of membranous over nonmembranous conservation ratios (identity)
                hist_data_AAIMON_mean = np.array(df_nonGPCR['AAIMON_mean_all_TMDs'].dropna())
                # use numpy to create a histogram
                freq_counts_I, bin_array_I = np.histogram(hist_data_AAIMON_mean, bins=binlist)
                # normalize the frequency counts
                freq_counts_normalised = freq_counts_I / freq_counts_I.max()
                # assuming all of the bins are exactly the same size, make the width of the column equal to 70% of each bin
                col_width = float('%0.3f' % (0.95 * (bin_array_I[1] - bin_array_I[0])))
                # when align='center', the central point of the bar in the x-axis is simply the middle of the bins ((bin_0-bin_1)/2, etc)
                centre_of_bar_in_x_axis = (bin_array_I[:-2] + bin_array_I[1:-1]) / 2
                # add the final bin, which is physically located just after the last regular bin but represents all higher values
                bar_width = centre_of_bar_in_x_axis[3] - centre_of_bar_in_x_axis[2]
                centre_of_bar_in_x_axis = np.append(centre_of_bar_in_x_axis, centre_of_bar_in_x_axis[-1] + bar_width)
                barcontainer_AAIMON_mean = ax.bar(left=centre_of_bar_in_x_axis,
                                                  height=freq_counts_normalised,
                                                  align='center', width=col_width, color='#B45F04',
                                                  alpha=0.5, linewidth=0.1)  # edgecolor='black',
                # other colours that are compatible with colourblind readers: #8A084B Dark red, #B45F04 deep orange, reddish purple #4B088A
                # http://html-color-codes.info/
                # label the x-axis for each plot, based on the TMD
                ax.set_xlabel('average conservation ratio (membranous over nonmembranous)',
                              fontsize=fontsize)
                # move the x-axis label closer to the x-axis
                ax.xaxis.set_label_coords(0.45, -0.085)
                xlim_min = 0.8
                xlim_max = 1.5
                ax.set_xlim(xlim_min, xlim_max)
                # set x-axis ticks
                # use the slide selection to select every second item in the list as an xtick(axis label)
                ax.set_xticks([float('%0.1f' % c) for c in centre_of_bar_in_x_axis[::3]])
                ax.set_ylabel('freq', rotation='vertical', fontsize=fontsize)
                # change axis font size
                ax.tick_params(labelsize=fontsize)
                # create legend?#http://stackoverflow.com/questions/9834452/how-do-i-make-a-single-legend-for-many-subplots-with-matplotlib
                legend_obj = ax.legend(['AAIMON GPCRs', 'AAIMON non-GPCRs'], loc='upper right',
                                       fontsize=fontsize)
                # add figure number to top left of subplot
                ax.annotate(s=str(Fig_Nr) + '.', xy=(0.04, 0.9), fontsize=fontsize, xytext=None,
                            xycoords='axes fraction', alpha=0.75)
                # add figure title to top left of subplot
                ax.annotate(s=title, xy=(0.1, 0.9), fontsize=fontsize, xytext=None, xycoords='axes fraction',
                            alpha=0.75)

                utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)
            else:
                sys.stdout.write('Dataset does not contain GPCRs; cannot create figure 19 \n')

        if s['Fig15_Boxplot_AAIMON_by_number_of_TMDs_GPCRs_only']:
            if True in df.GPCR:
                Fig_Nr = 15
                title = 'Only GPCRs, boxplot for each TMD'
                Fig_name = 'List{:02d}_Fig15_Boxplot_AAIMON_by_number_of_TMDs_GPCRs_only'.format(list_number)
                fig, ax = plt.subplots()
                # "#0489B1"
                alpha = 0.25
                col_width_value = 0.95
                ylabel = 'freq'
                xlabel = 'average conservation ratio (membranous over nonmembranous)'
                # legend =

                number_of_TMDs_excl_SP = df_GPCR.number_of_TMDs_excl_SP.max()
                legend = []
                data_to_plot = []
                for i in range(1, max_num_TMDs + 1):
                    TM = 'TM%02d' % i
                    hist_data_AAIMON_each_TM = df_GPCR['TM%02d_AAIMON_mean' % i].dropna()
                    if len(hist_data_AAIMON_each_TM) > 0:
                        data_to_plot.append(hist_data_AAIMON_each_TM)
                        legend.append(TM)

                meanpointprops = dict(marker='o', markerfacecolor='black', markersize=3)  # markeredgecolor='0.75',

                # flierprops = dict(marker='o', color = 'black', markerfacecolor='black', markersize=1)

                # flierprops = dict(marker='o',color='0.1', alpha=0.1)
                flierprops = dict(marker='o', markerfacecolor='green', markersize=12,
                                  linestyle='none')
                boxplotcontainer = ax.boxplot(data_to_plot, sym='+', whis=1.5, showmeans=True,
                                              meanprops=meanpointprops)
                ax.tick_params(labelsize=fontsize)
                for box in boxplotcontainer['boxes']:
                    # change outline color
                    box.set(color='black', linewidth=0.4)  # '7570b3'
                    # change fill color
                    # box.set( facecolor = '#1b9e77' )
                    box.set_linewidth(0.4)

                ## change color and linewidth of the whiskers
                for whisker in boxplotcontainer['whiskers']:
                    whisker.set(color='black', linewidth=0.4, dashes=(1, 1))

                ## change color and linewidth of the caps
                for cap in boxplotcontainer['caps']:
                    cap.set(color='black', linewidth=0.4)

                ## change color and linewidth of the medians
                for median in boxplotcontainer['medians']:
                    median.set(color='black', linewidth=0.4)

                # change the style of fliers and their fill
                for flier in boxplotcontainer['fliers']:
                    flier.set(marker='o', color='0.8', alpha=0.1, markerfacecolor='0.3', markersize=3)

                ## Remove top axes and right axes ticks
                ax.get_xaxis().tick_bottom()
                ax.get_yaxis().tick_left()
                ## Custom x-axis labels
                ax.set_xticklabels(legend, rotation=45)
                ax.set_ylabel('TM/nonTM conservation', fontsize=fontsize)
                # add figure number to top left of subplot
                ax.annotate(s=str(Fig_Nr) + '.', xy=(0.04, 0.9), fontsize=fontsize, xytext=None,
                            xycoords='axes fraction', alpha=0.75)
                # add figure title to top left of subplot
                ax.annotate(s=title, xy=(0.1, 0.9), fontsize=fontsize, xytext=None, xycoords='axes fraction',
                            alpha=0.75)

                utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)
            else:
                sys.stdout.write('Dataset does not contain GPCRs; cannot create figure 21 \n')

    if s['Fig16_Scatterplot_AAIMON_n_vs_slope']:
        Fig_Nr = 16
        title = 'AAIMON vs. AAIMON_slope'
        Fig_name = 'List{:02d}_Fig16_Scatterplot_AAIMON_n_vs_slope'.format(list_number)
        fig, ax = plt.subplots()

        x = df['AAIMON_mean_all_TMDs']
        y = df['AAIMON_slope_mean_all_TMDs']*1000

        if len(x) > 5:
            # calculate linear regression for fitted line
            linear_regression = np.polyfit(x, y, 1)
            fit_fn = np.poly1d(linear_regression)
            fitted_data_x = fit_fn(x)
            ax.plot(x, fitted_data_x, alpha=0.75, color='k')
            ax.annotate(s='y = {a:.5f}x + {b:.5f}'.format(a=linear_regression[0], b=linear_regression[1]), xy=(0.85, 0.95),
                        fontsize=fontsize-2, xytext=None, xycoords='axes fraction', alpha=0.75)
        else:
            logging.info("The dataset has less than 5 proteins. Lines of best fit will not be calculated.")

        ax.scatter(x, y, alpha=alpha_dpd, s=datapointsize)
        ax.set_ylabel(r'm$_{\rm TM/nonTM} *10^{\rm -3}$', rotation='vertical', fontsize=fontsize)
        ax.set_xlabel('TM/nonTM conservation', fontsize=fontsize)
        ax.annotate(s=str(Fig_Nr) + '.', xy=(0.04, 0.9), fontsize=fontsize, xytext=None,
                    xycoords='axes fraction', alpha=0.75)
        # add figure title to top left of subplot
        ax.annotate(s=title, xy=(0.1, 0.9), fontsize=fontsize, xytext=None, xycoords='axes fraction',
                    alpha=0.75)

        # change axis font size
        ax.tick_params(labelsize=fontsize)

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)


    if s['Fig17_Scatterplot_perc_identity_nonTMD_vs_TMD']:
        Fig_Nr = 17
        title = 'perc identity all TMDs  vs. perc identity nonTMD'
        Fig_name = 'List{:02d}_Fig17_Scatterplot_perc_identity_nonTMD_vs_TMD'.format(list_number)
        fig, ax = plt.subplots()

        x = df['TMD_perc_identity_mean_all_TMDs'] * 100
        y = df['nonTMD_perc_ident_mean'] * 100

        if len(x) > 5:
            linear_regression = np.polyfit(x, y, 1)
            fit_fn = np.poly1d(linear_regression)
            fitted_data_x = fit_fn(x)
            ax.plot(x, fitted_data_x, alpha=0.75, color='k')
            ax.annotate(s='y = {a:.5f}x + {b:.5f}'.format(a=linear_regression[0], b=linear_regression[1]),
                        xy=(0.85, 0.95), fontsize=fontsize - 2, xytext=None, xycoords='axes fraction',alpha=0.75)

        ax.scatter(x, y, s=datapointsize, alpha=alpha_dpd, color=color_list_TUM_blue)
        symmetrical = [s["min_ident"]*100, s["max_ident"]*100]
        ax.plot(symmetrical, symmetrical, color=color_list_TUM_blue[0], alpha=0.5, linestyle="-")
        ax.set_xlabel('TMD_perc_identity_all_TMDs', fontsize=fontsize)
        ax.set_ylabel('nonTMD_perc_ident_mean', rotation='vertical', fontsize=fontsize)
        ax.tick_params(labelsize=fontsize)
        ax.set_xlim(100-max_evol_distance, 100)
        ax.set_ylim(s["min_ident"]*100, 100)

        ax.annotate(s=str(Fig_Nr) + '.', xy=(0.04, 0.9), fontsize=fontsize, xytext=None,
                    xycoords='axes fraction', alpha=0.75)
        # add figure title to top left of subplot
        ax.annotate(s=title, xy=(0.1, 0.9), fontsize=fontsize, xytext=None, xycoords='axes fraction',
                    alpha=0.75)

        # change axis font size
        ax.tick_params(labelsize=fontsize)

        utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)

    if 'uniprot_KW' in df.columns:
        if s['Fig18_KW_assoc_with_large_number_of_homol']:
            Fig_Nr = 18
            title = 'keywords associated with many valid homologues'
            Fig_name = 'List{:02d}_Fig18_KW_assoc_with_large_number_of_homol'.format(list_number)

            # create cutoff, mean + 1 std
            cutoff = df.AAIMON_n_homol.mean() + df.AAIMON_n_homol.std()
            cutoff_int = int(np.round(cutoff))


            # convert stringlists to python lists
            if isinstance(df.uniprot_KW_for_analysis.dropna().iloc[0], str):
                df["uniprot_KW_for_analysis"] = df.uniprot_KW_for_analysis.dropna().apply(lambda x: ast.literal_eval(x))
            # get index of proteins with many or few homologues
            many_homol_index = df.AAIMON_n_homol.loc[df.AAIMON_n_homol > cutoff].index
            few_homol_index = df.AAIMON_n_homol.loc[df.AAIMON_n_homol <= cutoff].index
            # select subset of dataframe with many or few homologues
            df_few = df.loc[few_homol_index, :]
            df_many = df.loc[many_homol_index, :]
            # get a large list of keywords
            many_KW_list = df_many.uniprot_KW_for_analysis.dropna().tolist()
            few_KW_list = df_few.uniprot_KW_for_analysis.dropna().tolist()

            # convert list of keywords into pandas series, and use value_counts to count
            many_ser = pd.Series(utils.flatten(many_KW_list))
            few_ser = pd.Series(utils.flatten(few_KW_list))
            df_KW = pd.DataFrame()
            df_KW["many"] = many_ser.dropna().value_counts()
            df_KW["few"] = few_ser.dropna().value_counts()
            # total number of proteins with keyword (used as a cutoff)
            df_KW["total"] = df_KW["many"] + df_KW["few"]
            # fraction of proteins containing the keyword, in the many or few dataset
            df_KW["many_frac_containing_KW"] = df_KW.many / len(many_ser)
            df_KW["few_frac_containing_KW"] = df_KW.few / len(few_ser)
            # relative abundance of the keyword in the fraction with many homologues
            df_KW["relative_abundance_KW"] = df_KW["many_frac_containing_KW"] / df_KW["few_frac_containing_KW"]
            df_KW.sort_values("relative_abundance_KW", inplace=True, ascending=False)

            # only examine keywords with a significant number of proteins
            cutoff_min_num_prot_with_KW = 100
            df_KW_signif = df_KW.loc[df_KW.total > cutoff_min_num_prot_with_KW]

            fig, ax = plt.subplots()
            x = df_KW_signif.index
            y = df_KW_signif.many_frac_containing_KW
            y2 = df_KW_signif.few_frac_containing_KW
            width = 0.4
            x_ind = np.array(range(len(x))) + width
            ax.bar(left=x_ind, height=y, width=width, color="#0489B1", label=">{} homologues".format(cutoff_int))
            ax.bar(left=x_ind + width, height=y2, width=width, color="0.9", label="<{} homologues".format(cutoff_int))
            ax.set_xlim(0, x_ind[-1] + 1 + width / 2)
            ax.set_xticks(x_ind + width)
            ax.set_xticklabels(x, rotation=90)
            ax.set_ylabel("Fraction of proteins containing keyword")
            ax.legend(frameon=True)
            fig.tight_layout()
            utils.save_figure(fig, Fig_name, base_filepath, save_png, save_pdf, dpi)



    return "~~~~~~~~~~~~        run_save_figures_describing_proteins_in_list is finished        ~~~~~~~~~~~~"