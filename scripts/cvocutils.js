/***********************************************************************************
 * WARNING: These are legacy copies of scripts now hosted under the /services folder.
 *
 * THEY WILL NOT BE MAINTAINED AND MAY DISAPPEAR WITHOUT NOTICE.
 *
 * You are advised to not use them or configure to use any scripts hosted at gdcc.github.io/dataverse-external-vocab-support
 * except for testing.
 *
 * The current scripts, which are being maintained and updated, are under the /services directory.
 * To use them, follow the new local download/install instructions in the repository readme.
 */

//Common Methods - used in more than one script

// Put the text in a result that matches the term in a span with class
// select2-rendered__match that can be styled (e.g. bold)
function markMatch2(text, term) {
    // Find where the match is
    var match = text.toUpperCase().indexOf(term.toUpperCase());
    var $result = $('<span></span>');
    // If there is no match, move on
    if (match < 0) {
        return $result.text(text);
    }

    // Put in whatever text is before the match
    $result.text(text.substring(0, match));

    // Mark the match
    var $match = $('<span class="select2-rendered__match"></span>');
    $match.text(text.substring(match, match + term.length));

    // Append the matching text
    $result.append($match);

    // Put in whatever is after the match
    $result.append(text.substring(match + term.length));

    return $result;
}

function storeValue(prefix, id, value) {
    try {
        if(localStorage.getItem(prefix + id)==null) {
            // Store the most recent 1000 values across all scripts
            //ToDo: Use IndexedDB to manage storage for each script separately and avoid impacting other tools using localStorage
            if (localStorage.length > 1000) {
                localStorage.removeItem(localStorage.key(0));
            }
            localStorage.setItem(prefix + id, value);
        }
    } catch (e) {
        console.log("Problem using localStorage: " + e);
    }
}

function getValue(prefix, id) {
    try {
        let altNames='';
        let name = localStorage.getItem(prefix + id);
        if(name !== null) {
            let pos = name.indexOf('#');
            if(pos > 0) {
                altNames=name.substring(pos+1).split(',');
                name=name.substring(0, pos);
            }
        }
        return {name, altNames};
    } catch (e) {
        console.log("Problem getting value from localStorage: " + e);
    }
}

/**
 * Injects common CSS styles for CVOC scripts, specifically for Select2 search results.
 */
function injectCvocStyles() {
    if ($('#cvoc-styles').length === 0) {
        $('<style id="cvoc-styles">')
            .prop('type', 'text/css')
            .html(`
                .cvoc-extra-info {
                    font-size: 0.85em;
                    color: #777;
                    margin-left: 0px;
                }
                .select2-results__option--highlighted .cvoc-extra-info,
                .select2-highlighted .cvoc-extra-info {
                    color: #fff !important;
                }
            `)
            .appendTo('head');
    }
}