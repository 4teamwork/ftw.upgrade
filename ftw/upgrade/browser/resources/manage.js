(function($) {

    $('.select-none').live('click', function(e) {
        e.preventDefault();
        $('.profiles input[type=checkbox]').attr('checked', false);
    });

    $('.select-not-installed').live('click', function(e) {
        e.preventDefault();
        $('.profiles input[type=checkbox]').attr('checked', false);
        $('.profiles .upgrade.proposed input[type=checkbox]').attr(
            'checked', true);
    });

    $('.profile-title strong').live('click', function(e){
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

    $('.upgrade').live('click', function(e) {
        if($(e.target).is('input[type=checkbox]')) {
            return;
        }
        var checkbox = $('input[type=checkbox]', $(this));
        checkbox.attr('checked', checkbox.attr('checked') ? '' : 'checked');
    });

    $('#upgrade-form').live('submit', function(e) {
        $(this).hide();
        $('#back-to-upgrades').show();

        var height = ($('#portal-column-one').height() -
                      $('#portal-column-content').height());
        $('#upgrade-output').show();
        if(height > 0) {
            $('#upgrade-output').css('height', height);
        }
    });

    $('#back-to-upgrades').live('click', function(e) {
        location.reload();
    });

    $(document).ready(function() {
        $('[data-human-readable-version]').each(function() {
            $(this).data('original-version', $(this).text());
            $(this).text($(this).data('human-readable-version'));
        }).on('mouseenter', function(event) {
            $(this).text($(this).data('original-version'));
        }).on('mouseleave', function(event) {
            $(this).text($(this).data('human-readable-version'));
        });
    });

})(jQuery);
