$(document).ready(function() {
    // Clear all checkboxes when "Select None" is clicked
    $('.select-none').click(function(e) {
        e.preventDefault();
        $('.profiles input[type=checkbox]').prop('checked', false);
    });

    // Select all addons yet to be installd
    $('.select-not-installed').click(function(e) {
        e.preventDefault();
        $('.profiles input[type=checkbox]').prop('checked', false);
        $('.profiles .upgrade.proposed input[type=checkbox]').prop('checked', true);
    });

    // Show/hide addon's completed upgrades
    $('.profiles .profile-title strong').click(function(e){
        e.preventDefault();
        var profile = $(this).parents('.profile:first');
        var to_visible = profile.hasClass('hide-done');
        profile.toggleClass('hide-done');
        profile.find('.upgrade.done').each(function() {
            if(to_visible) {
                $(this).show();
            } else if(!$(this).find('input[type=checkbox]').attr('checked')) {
                $(this).hide();
            }
        });
    });

    // Check checkbox for upgrade step if upgrade name is clicked
    $('.profiles .upgrade').click(function(e) {
        if($(e.target).is('input[type=checkbox]')) {
            return;
        }
        var checkbox = $('input[type=checkbox]', $(this));
        checkbox.prop('checked', !checkbox.prop('checked'));
    });

    // Hide the upgrade form while an upgrade is being installed
    $('#upgrade-form').submit(function(e) {
        $(this).hide();
        $('#back-to-upgrades').show();

        var height = ($('#portal-column-one').height() -
                      $('#portal-column-content').height());
        $('#upgrade-output').show();
        if(height > 0) {
            $('#upgrade-output').css('height', height);
        }
    });

    // Allow user to return to the upgrades form after installing an upgrade
    $('#back-to-upgrades').click(function(e) {
        location.reload();
    });

    $('[data-human-readable-version]').each(function() {
        $(this).data('original-version', $(this).text());
        $(this).text($(this).data('human-readable-version'));
    }).on('mouseenter', function(event) {
        $(this).text($(this).data('original-version'));
    }).on('mouseleave', function(event) {
        $(this).text($(this).data('human-readable-version'));
    });
});
