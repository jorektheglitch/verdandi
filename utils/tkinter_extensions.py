import asyncio

import tkinter as tk
import tkinter.ttk as ttk


DELAULT_TABLE_IDENTITY = 2


class AioTk(tk.Tk):

    def __init__(self, *args, delay=1/50, **kwargs):
        super().__init__(*args, **kwargs)
        self._delay = delay
        self._loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.updater(), loop=self._loop)

    async def updater(self):
        while True:
            try:
                self.update()
            except Exception:
                self._loop.stop()
                break
            else:
                await asyncio.sleep(self._delay)
    
    def mainloop(self, n=0):
        self._loop.run_forever()


class Table(tk.Frame):
    __slots__ = []
    def __init__(
            self, parent=None, headings=(), unique_heading=None, params=(),
            updater=None, updater_exc_handler=None, update_delay=5, 
            identity_lvl=DELAULT_TABLE_IDENTITY, name=None
        ):
        super().__init__(parent, name=name)

        table = ttk.Treeview(self, show="headings", selectmode="extended")
        table["columns"]=headings
        table["displaycolumns"]=headings

        for head in headings:
            table.heading(head, text=head, anchor=tk.CENTER, command= self.sort_column(head))
            table.column(head, anchor=tk.CENTER, width=150)

        yscrolltable = tk.Scrollbar(self, command=table.yview)
        xscrolltable = tk.Scrollbar(self, command=table.xview, orient=tk.HORIZONTAL)
        table.configure(yscrollcommand=yscrolltable.set)
        table.configure(xscrollcommand=xscrolltable.set)
        yscrolltable.pack(side=tk.RIGHT, fill=tk.Y)
        xscrolltable.pack(side=tk.BOTTOM, fill=tk.X)

        table.place(relheight=1, relwidth=1, relx=0, rely=0)
        self.tv = table
        
        self.uniques = {}
        if unique_heading:
            self.uh_index = headings.index(unique_heading)
        self.names = params
        self._paused = False
        self._ident_lvl = identity_lvl
        if updater:
            self._updater = updater
            asyncio.ensure_future(self.updater(updater, update_delay))
        self.upd_exc_handler = updater_exc_handler if updater_exc_handler else lambda *args, **kwargs: None
        self.replicants = []

    def add_row(self, row):
        new_id = self.tv.insert('', tk.END, values=tuple(row))
        self.uniques[row[self.uh_index]] = new_id
    
    def add_rows(self, rows):
        for row in rows:
            self.add_row(row)
    
    def add_replicant(self, replicant):
        if isinstance(replicant, type(self)):
            self.replicants.append(replicant)
        else:
            raise TypeError('replicant must be Table instance')
    
    def replicants_updater(self, update):
        for replicant in self.replicants:
            replicant.raw_update_table(update)

    async def updater(self, updater, delay:int):
        updater = asyncio.coroutine(updater)
        while True:
            while not self._paused:
                try:
                    raw = await updater()
                except Exception as e:
                    self.upd_exc_handler(e)
                else:
                    rows = tuple(tuple(item[name] for name in self.names) for item in raw)
                    self.update_table(rows, self._ident_lvl)
                    self.replicants_updater(raw)
                finally:
                    await asyncio.sleep(delay)
            await asyncio.sleep(delay)
    
    async def update_nowait(self):
        self.pause()
        raw = await asyncio.coroutine(self._updater())
        rows = ((item[name] for name in self.names) for item in raw)
        self.update_table(rows, self._ident_lvl)
        self.run()
    
    def pause(self):
        self._paused = True

    def run(self):
        self._paused = False

    def bind_menu(self, menu:tk.Menu):
        def call_menu(event: tk.Event):
            menu.post(event.x_root, event.y_root)
        self.tv.bind("<Button-3>", call_menu)

    def delete_selected(self, event:tk.Event):
        pass

    def clean(self):
        parent = ''
        items = self.tv.get_children(parent)
        self.tv.delete(*items)
    
    def _similarity(self, one, other):
        return sum(ones==others for ones, others in zip(one, other))
    
    def _find_similar(self, row, identity_lvl):
        for iid in self.tv.get_children(''):
            item = self.tv.item(iid)
            similarity = self._similarity(item['values'], row)
            if similarity>=identity_lvl:
                return iid

    def update_table(self, rows, identity_lvl=None):
        if not identity_lvl:
            if self._ident_lvl:
                identity_lvl = self._ident_lvl
            else:
                identity_lvl = len(self.names)
        for row in rows:
            row = tuple(row)
            if row[self.uh_index] in self.uniques:
                self.tv.item(self.uniques[row[self.uh_index]], values=row)
            else:
                self.add_row(row)
        if hasattr(self, 'last_sort'):
            self.last_sort()

    def raw_update_table(self, raw):
        rows = tuple(tuple(item[name] for name in self.names) for item in raw)
        self.update_table(rows)

    def sort_column(self, column, reverse=False):
        def sorter():
            l = [(self.tv.set(k, column), k) for k in self.tv.get_children('')]
            l.sort(reverse=reverse)
            # rearrange items in sorted positions
            for index, (_, k) in enumerate(l):
                self.tv.move(k, '', index)
            self.last_sort = self.sort_column(column, reverse)
            self.tv.heading(column, command= self.sort_column(column, not reverse))
        return sorter


class VarsUpdater():
    def __init__(self):
        self.groups = {}
    def add(self, var, group_name):
        self.groups[group_name]['vars'].append(var)


class AutoUpdatingVar():

    __slots__ = ['var', 'type_coercion', 'delay']
    comparison = {
        tk.BooleanVar: bool,
        tk.DoubleVar: float,
        tk.IntVar: int,
        tk.StringVar: str
    }

    def __init__(self, var:tk.Variable, updater, delay=5):
        self.var = var
        self.type_coercion = self.comparison.get(type(var), str)
        self.delay = delay
        asyncio.ensure_future(self.updater(updater))

    async def updater(self, source):
        updater = asyncio.coroutine(source)
        while True:
            upd = self.type_coercion(await updater())
            self.var.set(upd)
            await asyncio.sleep(self.delay)


class FStringVar(tk.StringVar):
    def __init__(self, *args, template:str, fargs:list, fkwargs:dict, **kwargs):
        self.templ = template
        kwargs['value'] = template.format(*fargs, **fkwargs)
        super().__init__(*args, **kwargs)
    def set(self, *args, **kwargs):
        upd = self.templ.format(*args, **kwargs)
        super().set(upd)