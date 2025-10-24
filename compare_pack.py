import filecmp
import tkinter as tk
from tkinter import ttk, LEFT, TOP
from tkinter import filedialog as fd


def select_directory1():
    directory_name = fd.askdirectory()
    d1_text.set(directory_name)


def select_directory2():
    directory_name = fd.askdirectory()
    d2_text.set(directory_name)


def compare_directories():
    # compares directories
    result = filecmp.dircmp(d1_text.get(), d2_text.get())
    # finds similarly-named files
    result_matching_name_list.set(result.common.__str__())
    # finds similarly-named files that have SAME contents
    result_identical_list.set(result.same_files.__str__())
    # finds similarly-named files that have DIFF contents
    result_conflicting_list.set(result.diff_files.__str__())
    # finds similarly-named directories
    # result_matching_directory_list.set(result.common_dirs.__str__())

    # ---------- finds differing files ----------
    result_1 = result.left_list
    result_2 = result.right_list
    diff_array_1 = []
    diff_array_2 = []

    for file in result_1:
        if file not in result_2:
            diff_array_1.append(file)

    result_diff_files_list_1.set(diff_array_1.__str__())

    for file in result_2:
        if file not in result_1:
            diff_array_2.append(file)

    result_diff_files_list_2.set(diff_array_2.__str__())

    # ----- reads each conflicting file and displays the contents -----
    conflicting_files = result.diff_files

    for file in conflicting_files:
        file_opener1 = open(d1_text.get() + "/" + file, "r")
        file_opener2 = open(d2_text.get() + "/" + file, "r")

        file_reader1 = file_opener1.read()
        file_reader2 = file_opener2.read()

        d1_result_diff_files.set(file_reader1)
        d2_result_diff_files.set(file_reader2)

        file_opener1.close()
        file_opener2.close()


# ----- main GUI window -----
window = tk.Tk()
window.geometry("800x600")
window.title("Comparyson")

# ----- StringVars -----
d1_text = tk.StringVar()
d2_text = tk.StringVar()
result_matching_name_list = tk.StringVar()
result_conflicting_list = tk.StringVar()
result_identical_list = tk.StringVar()
result_diff_files_list_1 = tk.StringVar()
result_diff_files_list_2 = tk.StringVar()
d1_result_diff_files = tk.StringVar()
d2_result_diff_files = tk.StringVar()

# ----------------- selected directories -------------------

# labels for selected directories
d1_label = tk.Label(window, text="Directory 1:")
d1_label.pack(side=TOP, padx=200)
d2_label = tk.Label(window, text="Directory 2:")
d2_label.pack(side=TOP)
d1 = tk.Label(window, textvariable=d1_text)
d2 = tk.Label(window, textvariable=d2_text)
d1.pack()
d2.pack()

open_button1 = ttk.Button(
    window,
    text='Open Directory',
    command=select_directory1
)
open_button1.pack()

open_button2 = ttk.Button(
    window,
    text='Open Directory',
    command=select_directory2
)
open_button2.pack()

# call compare_directories()
compare_button = tk.Button(window, text='Compare', command=compare_directories)
compare_button.pack()

# ----------------------- results ---------------------------

# labels for the result fields
same_name_label = tk.Label(window, text="Same file names:")
identical_label = tk.Label(window, text="Identical files:")
conflicting_label = tk.Label(window, text="Conflicting Files:")
diff1_label = tk.Label(window, text="Different Files (d1):")
diff2_label = tk.Label(window, text="Different Files (d2):")
same_name_label.pack()
identical_label.pack()
conflicting_label.pack()
diff1_label.pack()
diff2_label.pack()

# result fields
match_answer_label = tk.Label(window, textvariable=result_matching_name_list)
identical_answer_label = tk.Label(window, textvariable=result_identical_list)
conflicting_files_label = tk.Label(window, textvariable=result_conflicting_list)
diff_files_label1 = tk.Label(window, textvariable=result_diff_files_list_1)
diff_files_label2 = tk.Label(window, textvariable=result_diff_files_list_2)
match_answer_label.pack()
identical_answer_label.pack()
conflicting_files_label.pack()
diff_files_label1.pack()
diff_files_label2.pack()

# printed file labels
d1_file_label = tk.Label(window, text="d1 file:")
d2_file_label = tk.Label(window, text="d2 file:")
d1_diff_file_label = tk.Label(window, textvariable=d1_result_diff_files)
d2_diff_file_label = tk.Label(window, textvariable=d2_result_diff_files)
d1_file_label.pack()
d2_file_label.pack()
d1_diff_file_label.pack()
d2_diff_file_label.pack()

# --------------------- notebook ---------------------------

# create notebook
notebook = ttk.Notebook(window)
notebook.pack()

# create frames
frame1 = ttk.Frame(notebook)
frame2 = ttk.Frame(notebook)
frame1.pack(fill='both', expand=False)
frame2.pack(fill='both', expand=False)

# add frames to notebook
notebook.add(frame1, text='General Information')
notebook.add(frame2, text='Profile')

window.mainloop()
tk.mainloop()

# D:/projects-coding/python/python-comparison/d1
# D:/projects-coding/python/python-comparison/d2

# TODO - Change to pack layout?
# TODO - Add tabs or buttons to show each file comparison
# TODO - Compare line-by-line and -- show the differences on the GUI
# TODO - List subdirectories/ their files and compare those
# TODO - Add error handling
# TODO - Add limits to prevent memory leaks, crashes, etc.
# TODO - Prevent from being run multiple times?
