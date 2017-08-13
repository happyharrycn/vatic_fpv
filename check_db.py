import argparse
import sqlite3
import matplotlib.pyplot as plt

def main(video_db_file):
    video_db = sqlite3.connect(video_db_file)
    db_cursor = video_db.cursor()

    print "Naming tasks"
    db_cursor.execute('''SELECT DISTINCT named_by_user FROM video_db WHERE named=1''')
    user_names = db_cursor.fetchall()

    labels = []
    sizes = []
    explode = []

    for user_name in user_names:
        db_cursor.execute('''SELECT count(*) FROM video_db WHERE named_by_user=?''', user_name)
        num_tasks = db_cursor.fetchone()[0]

        db_cursor.execute('''SELECT count(*) FROM video_db WHERE named_by_user=? AND red_flag>0''', user_name)
        num_flags = db_cursor.fetchone()[0]

        print "User: {:s}, Name Task finished: {:d} (Red flag {:0.2f}%)".format(
            user_name[0], num_tasks, 100*float(num_flags)/float(num_tasks))

        labels.append(str(user_name[0]))
        sizes.append(num_tasks)
        explode.append(0)

    idx = sizes.index(max(sizes))
    explode[idx] = 0.1

    total_num_tasks = sum(sizes)
    sizes = [float(num)/float(total_num_tasks) for num in sizes]
    print "Total Name Task finished: {:d} ".format(total_num_tasks)

    for idx in xrange(len(sizes)):
        if sizes[idx] <= 0.03:
            labels[idx] = ''

    fig1, ax1 = plt.subplots()
    patches, texts, autotexts = ax1.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
        shadow=True, startangle=90)
    ax1.axis('equal')
    for idx in xrange(len(texts)):
        texts[idx].set_fontsize(20)

    plt.show()


if __name__ == '__main__':
    description = 'Helper script for get stats from db.'
    p = argparse.ArgumentParser(description=description)
    p.add_argument('video_db_file', type=str,
                   help='Video db file')
    main(**vars(p.parse_args()))