from ftw.upgrade.cockpit.cluster import ZooKeeper
from ftw.upgrade.cockpit.exceptions import AllWorkersFinished
from ftw.upgrade.utils import distribute_across_columns
import urwid
import sys


PALETTE = [
    ('pg normal',    'white',        'black', 'standout'),
    ('pg complete',  'white',        'light blue'),
    ('pg smooth',    'light blue',   'black'),
    ('ftw blue',     'light blue',   'black'),
    ('ftw white',    'white',   'black'),
    ]


def make_pb():
    """Create a ProgressBar widget.
    """
    return urwid.ProgressBar('pg normal', 'pg complete')


if '--mock' in sys.argv:
    from ftw.upgrade.cockpit.cluster import MockZooKeeper
    ZooKeeperClass = MockZooKeeper
else:
    ZooKeeperClass = ZooKeeper


class CockpitApplication(ZooKeeperClass):
    """Management interface to run several upgrades in parallel.

    The actual management of the spawned subprocesses is handled by the
    ZooKeeper class, this just wires it together into a nice textual user
    interface using urwid.
    """

    def __init__(self, cluster_dir=None):
        self.loop = None
        ZooKeeperClass.__init__(self, cluster_dir)

    def update_progress(self, progress_info):
        """Takes a (worker_number, progress) tuple and updates the ProgressBar
        in the corresponding widget with the new progress.
        """
        columns = self.loop.widget.get_body().get_body()
        left_col = columns.widget_list[0]
        right_col = columns.widget_list[1]
        items = left_col.widget_list + right_col.widget_list

        worker_number, progress = progress_info
        items[worker_number - 1].widget_list[1].set_completion(progress * 100)
        self.loop.draw_screen()

    def update_status_bar(self, text):
        self.status_bar.set_text(text)
        self.loop.draw_screen()

    def check_for_progress(self):
        """Callback method that gets called whenever a child process signals
        availability of new progress updates via the `self.parent_conn` pipe.

        ZooKeeper's poll_progress_info() actually retrieves the progress
        updates from the shared queue and calls this class' update_progress()
        method if there are any updates.
        """
        try:
            self.poll_progress_info()
        except AllWorkersFinished:
            self.clean_up_runners()
            raise urwid.ExitMainLoop

    def setup_ui(self):
        # Build a flat list of Text + ProgressBar widgets, one for each worker
        worker_widgets = []
        for buildout in self.buildouts:
            worker_widgets.append(urwid.Columns([urwid.Text(buildout), make_pb()]))

        # Then distribute them evenly across two columns
        worker_widgets = distribute_across_columns(worker_widgets, 2)
        cols = urwid.Columns([urwid.Pile(col) for col in worker_widgets],
                             dividechars=2)

        fill = urwid.Filler(cols, 'top')

        title = urwid.Text([('ftw blue', "4"), ('ftw white', "teamwork"), u" ftw.upgrade Cockpit"])
        title = urwid.Columns([title])

        header = urwid.Pile([title, urwid.Divider('-')])
        self.status_bar = urwid.Text(('status normal', ''))
        footer = urwid.Pile([urwid.Divider('-'), self.status_bar])
        frame = urwid.Frame(body=fill, header=header, footer=footer)

        self.loop = urwid.MainLoop(frame, PALETTE)

    def launch_runners(self, loop, user_data):
        self.update_status_bar('Spawning upgrade runners...')
        self.spawn_runners()
        self.update_status_bar('Done spawning runners.')
        # Register check_for_progress() as a callback to be called
        # whenever there's activity on the pipe `parent_conn` (which
        # the spawned child processes will use to signal available updates)
        self.loop.watch_file(self.parent_conn, self.check_for_progress)
        self.update_status_bar('Watching for progress updates...')

    def run(self):
        self.setup_ui()
        self.loop.set_alarm_in(0, self.launch_runners)
        try:
            self.loop.run()
        except KeyboardInterrupt:
            print "Caught KeyboardInterrupt."
        finally:
            self.clean_up_runners()
            print "All runners terminated cleanly."
