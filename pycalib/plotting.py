# Standard imports
import numpy as np
import scipy.stats
import pandas as pd

# matplotlib
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText

# scikit-learn
import sklearn.metrics

# Package imports
import pycalib.scoring
import pycalib.texfig as texfig


def reliability_diagram(y, p_pred, filename, title="Reliability Diagram", n_bins=100, show_ece=False, xlim=None):
    """
    Plot a reliability diagram

    This function plots the reliability diagram [1]_ [2]_ and histograms from the given confidence estimates. Reliability diagrams
    are a visual aid to determine whether a classifier is calibrated or not.

    Parameters
    ----------
    y : array, shape = [n_methods, n_samples]
        Ground truth labels.
    y_pred : array, shape = [n_methods, n_samples]
        Predicted labels.
    p_pred : array
        Array of confidence estimates
    filename : str
        Path or name of output plot files.
    title : str
        Title of plot.
    n_bins : int, optional, default=20
        The number of bins into which the `y_pred` are partitioned.
    show_ece : bool
        Whether the expected calibration error (ECE) should be displayed in the plot.
    xlim : array, shape = (2,), default=None
        X-axis limits. If note provided inferred from y.

    References
    ----------
    .. [1] DeGroot, M. H. & Fienberg, S. E. The Comparison and Evaluation of Forecasters. Journal of the Royal
           Statistical Society. Series D (The Statistician) 32, 12–22.
    .. [2] Niculescu-Mizil, A. & Caruana, R. Predicting good probabilities with supervised learning in Proceedings of
           the 22nd International Conference on Machine Learning (2005)

    """
    # Initialization
    if xlim is None:
        n_classes = len(np.unique(y))
        xlim = [1 / n_classes, 1]

    y_pred = np.argmax(p_pred, axis=1)
    p_max = np.max(p_pred, axis=1)

    # Define bins
    bins = np.linspace(xlim[0], xlim[1], n_bins + 1)

    # Plot reliability diagram
    fig, axes = texfig.subplots(nrows=2, ncols=1, width=4, ratio=1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})

    # Calibration line
    axes[0].plot(xlim, xlim, linestyle='--', color='grey', label='Calibrated Output')

    # Compute bin means and empirical accuracy
    bin_means = np.linspace(xlim[0] + xlim[1] / (2 * n_bins), xlim[1] - xlim[1] / (2 * n_bins), n_bins)
    empirical_acc = scipy.stats.binned_statistic(p_max,
                                                 np.equal(y_pred, y).astype(int),
                                                 bins=n_bins,
                                                 range=xlim)[0]
    empirical_acc[np.isnan(empirical_acc)] = bin_means[np.isnan(empirical_acc)]

    # Plot accuracy
    axes[0].step(bins, np.concatenate(([xlim[0]], empirical_acc)), '-', label='Classifier Output')
    x = np.linspace(xlim[0], xlim[1], 1000)
    bin_ind = np.digitize(x, bins)[1:-1] - 1
    axes[0].fill_between(x[1:-1], x[1:-1], (bin_means + (empirical_acc - bin_means))[bin_ind], facecolor='k', alpha=0.2)
    axes[0].set_ylabel('Accuracy')
    axes[0].legend(loc='upper left')
    if title is not None:
        axes[0].set_title(title)

    # Plot histogram
    hist, ex = np.histogram(p_max, bins=bins)
    axes[1].fill_between(bins, np.concatenate(([0], hist / np.sum(hist))), lw=0.0, step="pre")
    axes[1].set_xlabel('Maximum Probability $z_{\\textup{max}}$')
    axes[1].set_ylabel('Sample Fraction')
    axes[1].set_xlim(xlim)
    fig.align_labels()

    # Add textbox with ECE
    if show_ece:
        ece = pycalib.scoring.expected_calibration_error(y=y, p_pred=p_pred, n_bins=n_bins)
        anchored_text = AnchoredText("$\\textup{ECE}_1 = " + "{:.3f}$".format(ece), loc='lower right')
        anchored_text.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")
        anchored_text.patch.set_edgecolor("0.8")
        anchored_text.patch.set_alpha(0.9)
        axes[0].add_artist(anchored_text)

    # Save to file
    texfig.savefig(filename=filename)


def confidence_diagram(y, y_pred, p_pred, n_classes=None, file=None, plot=True, n_bins=20, color=None, **kwargs):
    """
    Plot a confidence diagram

    Plots a diagram showing both distributions of over- and underconfidence.

    Parameters
    ----------
    y : array, shape = [n_samples]
        Ground truth labels.
    y_pred : array, shape = [n_samples]
        Predicted labels.
    p_pred : array, shape = [n_samples, n_classes]
        Array of confidence estimates.
    file : str, optional
        File name of output plot.
    plot : bool
        Should the generated plot be shown?
    n_bins: int, optional, default=20
        Number of bins to use for the histograms.
    """

    # Determine number of classes
    if n_classes is None:
        n_classes = len(np.unique(y))

    # Find prediction confidence
    p_max = np.max(p_pred, axis=1)

    # Define bins
    bins = np.linspace(0, 1, n_bins + 1)

    # Plot overconfidence
    plt.subplot(2, 1, 1)
    plt.hist(p_max[y != y_pred], range=[1 / n_classes, 1], bins=bins, color=color, **kwargs)
    plt.axvline(pycalib.scoring.overconfidence(y, y_pred, p_pred), linewidth=3, color='k')
    plt.xlim([1 / n_classes, 1])
    plt.ylabel('Count')
    plt.title('Confidence of false predictions')

    # Plot 1 - underconfidence
    plt.subplot(2, 1, 2)
    plt.xlim([1 / n_classes, 1])
    plt.hist(p_max[y == y_pred], range=[1 / n_classes, 1], bins=bins, color=color, **kwargs)
    plt.axvline(1 - pycalib.scoring.underconfidence(y, y_pred, p_pred), linewidth=3, color='k')
    plt.xlabel('Predicted Probability')
    plt.ylabel('Count')
    plt.title('Confidence of correct predictions')

    # Save plot
    plt.subplots_adjust(hspace=0.5)
    if file is not None:
        plt.savefig(file)
    if plot:
        plt.show()

    return plt


def over_underconfidence_curve(y, y_pred, p_pred, file=None, plot=True, n_bins=1000, **kwargs):
    """
    Plot an over-/underconfidence curve

    Plots a diagram showing a precision/recall type curve for over- and underconfidence [1]_.

    Parameters
    ----------
    y : array, shape = [n_samples]
        Ground truth labels.
    y_pred : array, shape = [n_samples]
        Predicted labels.
    p_pred : array, shape = [n_samples, n_classes]
        Array of confidence estimates.
    file : str, optional
        File name of output plot.
    plot : bool
        Should the generated plot be shown?
    n_bins: int, optional, default=20
        Number of bins to use for the histograms.

    References
    ----------
    .. [1] Mund, D. et al. Active online confidence boosting for efficient object classification

    """

    # Find correct predictions
    pred_correct = np.equal(y, y_pred)

    # Compute confidence on false and correct predictions
    p_max = np.max(p_pred, axis=1)
    conf_correct = p_max[pred_correct]
    conf_false = p_max[np.invert(pred_correct)]

    # Compute cumulative statistics of overconfidence and underconfidence curves
    bins = np.linspace(0, 1, n_bins)

    conf_false_hist = np.histogram(conf_false, bins=bins)[0]
    conf_false_cum = np.cumsum(conf_false_hist) / np.sum(conf_false_hist)

    conf_correct_hist = np.histogram(conf_correct, bins=bins)[0]
    conf_correct_cum = np.cumsum(conf_correct_hist) / np.sum(conf_correct_hist)

    # Plot over-/underconfidence curve
    plt.figure(0, figsize=(6, 6))
    plt.plot([0., 1.], [1., 0.], '--', color='grey', alpha=.75)
    plt.plot(conf_false_cum, 1 - conf_correct_cum, **kwargs)
    plt.xlabel('false and uncertain')
    plt.ylabel('correct and confident')
    plt.title('Over-/Underconfidence curve')

    # Save plot
    if file is not None:
        plt.savefig(file)
    if plot:
        plt.show()

    return plt


def confidence_trajectories(y, y_pred, p_pred, plot_calibration=True, n_classes=None, n_thresh_steps=1000, file=None,
                            plot=True, **kwargs):
    # Find number of classes and correct predictions
    if n_classes is None:
        n_classes = len(np.unique(y))
    pred_correct = np.equal(y, y_pred)

    # Compute accuracy and inverse odds
    accuracy = np.mean(pred_correct)
    inv_odds = (1 - accuracy) / accuracy

    # Compute confidence and uncertainty on false and correct predictions
    p_max = np.max(p_pred, axis=1)
    conf_correct = np.sort(p_max[pred_correct])
    conf_false = np.sort(p_max[np.invert(pred_correct)])

    # Compute cumulative statistics of overconfidence and underconfidence curves
    def index_of_max_element_below_thresh(elements, threshold):
        if np.min(elements) > threshold:
            return 0
        else:
            return np.argmax(elements[elements <= threshold])

    conf_thresholds = np.linspace(1 / n_classes, 1, n_thresh_steps)

    max_els_conf_correct = [index_of_max_element_below_thresh(conf_correct, thresh) for thresh in conf_thresholds]
    max_els_conf_false = [index_of_max_element_below_thresh(conf_false, thresh) for thresh in conf_thresholds]

    cummean = lambda x: x.cumsum() / np.arange(1, len(x) + 1)

    avg_conf_correct = cummean(conf_correct)[max_els_conf_correct]
    avg_conf_false = cummean(conf_false)[max_els_conf_false]

    if plot_calibration:
        # Plot calibration corridor
        o = np.arange(0.5, 1.01, 0.01)
        u = inv_odds * o

        # TODO: solve situation with different accuracies and ECE
        # TODO: (use only methods which do not change accuracy and plot max calibration error, except for uncalibrated?)
        u_upper_bound = inv_odds * o + pycalib.scoring.expected_calibration_error(y, y_pred, p_pred) / accuracy
        u_lower_bound = inv_odds * o - pycalib.scoring.expected_calibration_error(y, y_pred, p_pred) / accuracy

        plt.fill_between(o, u_upper_bound, u_lower_bound, alpha=.3, color='gray')
        plt.plot(o, u, '--', color='gray')

    # Plot trajectories
    plt.figure(0, figsize=(6, 6))
    plt.plot(avg_conf_false, 1 - avg_conf_correct, **kwargs)

    # Plot over- and underconfidence
    kwargs['label'] = '_nolegend_'
    plt.plot(pycalib.scoring.overconfidence(y, y_pred, p_pred), pycalib.scoring.underconfidence(y, y_pred, p_pred), 'o',
             **kwargs)

    # Set plot parameters
    plt.ylim(0, 1 - 1 / n_classes)
    plt.xlim(1 / n_classes, 1)
    plt.xlabel('Avg. confidence of false')
    plt.ylabel('Avg. uncertainty of correct')
    plt.title('Over- and underconfidence trajectories')

    # Save plot
    if file is not None:
        plt.savefig(file)
    if plot:
        plt.show()

    return plt


def logsumexp_illustration(file=None, plot=True):
    # Define maximum approximation: logsumexp
    def logsumexp(x, N):
        return 1 / N * np.log(np.sum(np.exp(N * x), axis=1))

    # Plot for two different N
    N1 = 5
    N2 = 50
    N3 = 500

    t1 = np.arange(0.0, 1.0, 0.01)

    plt.figure(0, figsize=(16, 3.5))

    ax1 = plt.subplot(1, 3, 1)
    plt.plot(t1, logsumexp(np.column_stack([1 - t1, t1]), N1), 'b', label="N = " + str(N1))
    plt.legend(fontsize='xx-large', loc=9)
    ax1.set_aspect('equal', 'box')

    ax2 = plt.subplot(1, 3, 2, sharey=ax1)
    plt.plot(t1, logsumexp(np.column_stack([1 - t1, t1]), N2), 'b', label="N = " + str(N2))
    plt.legend(fontsize='xx-large', loc=9)
    ax2.set_aspect('equal', 'box')

    ax3 = plt.subplot(1, 3, 3, sharey=ax1)
    plt.plot(t1, logsumexp(np.column_stack([1 - t1, t1]), N3), 'b', label="N = " + str(N3))
    plt.legend(fontsize='xx-large', loc=9)
    ax3.set_aspect('equal', 'box')

    # Save plot
    if file is not None:
        plt.savefig(file, bbox_inches='tight')
    if plot:
        plt.show()
