import re
import sys

import click
import praw
from ebooklib import epub


class NotFoundError(Exception):
    pass


reddit = praw.Reddit(client_id="sUBJ9ERh2RyjmQ", client_secret=None,
                     user_agent='Reddit storries to epub by mircohaug')


@click.command()
@click.option('input_url', '--input', '-i', required=True,
              help='The url of an arbitrary chapter of the series you want to convert')
@click.option('output_filename', '--output', '-o', default="",
              help='The filename of the output epub. Defaults to the first chapter title.')
@click.option('--overlap', default=10, help='How many common characters do the titles have at the beginning.')
def main(input_url: str, overlap, output_filename):
    initial_submission = reddit.submission(url=input_url)
    title = initial_submission.title
    author = initial_submission.author
    subreddit = initial_submission.subreddit

    list_of_posts = subreddit.search("author:{}".format(author), sort='new', limit=None)

    len_selected_submissions = 0
    selected_submissions = []
    for p in list_of_posts:
        len_selected_submissions += 1
        # starting with the same first 10 letters
        if p.subreddit == subreddit and p.title.startswith(title[:overlap]):
            if p.is_self:
                selected_submissions.append(p)
            else:
                # is crosspost if not likely media and ignored
                if hasattr(p, "crosspost_parent"):
                    original_post = list(reddit.info(fullnames=[p.crosspost_parent]))[0]
                    if not original_post.is_self:
                        # double crossposts not supported
                        continue
                    else:
                        selected_submissions.append(original_post)

    print("Total number of author posts in subreddit: {0}".format(len_selected_submissions))

    len_subs = len(selected_submissions)
    print("Number of applicaple posts {}".format(len_subs))
    if len_subs == 1:
        raise Exception("No other chapters found, which share the first {} characters with other posts from this "
                        "author in this subreddit.".format(overlap))
    elif len_subs == 0:
        raise Exception("No text chapters found")

    if len_selected_submissions >= 900:
        print("Got more than 900 submissions from author in this subreddit :-O. "
              "It may be possible that old chapters are not included.",
              file=sys.stderr)

    book = epub.EpubBook()

    # set metadata
    book.set_identifier(selected_submissions[-1].id)
    book.set_title(selected_submissions[-1].title)
    book.set_language('en')
    # replace all non alphanumeric chars through _ for filename sanitation
    if output_filename:
        file_name = output_filename
    else:
        file_name = (re.sub('[^0-9a-zA-Z]+', '_', selected_submissions[-1].title) + ".epub").strip("_OC")

    book.add_author(author.name)

    chapters = []

    print("Chapters:")

    # check for title prefix
    for i, sub in enumerate(reversed(selected_submissions)):
        # create chapter
        c1 = epub.EpubHtml(title=sub.title, file_name='chap_{}.xhtml'.format(i), lang='en')
        c1.content = "<h1>{}</h1>".format(sub.title) + sub.selftext_html

        # add chapter
        book.add_item(c1)
        chapters.append(c1)

        print(sub.title)

    # define Table Of Contents
    book.toc = (
        chapters
    )

    # add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # basic spine
    spine = ['nav']
    spine.extend(chapters)
    # is used to generate the toc at the start
    book.spine = spine

    # write to the file
    epub.write_epub(file_name, book, {})

    pass


if __name__ == '__main__':
    # todo setup.py
    main()
