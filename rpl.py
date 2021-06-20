import os
import sys


class RenameError(Exception):
    def __init__(self, msg=''):
        self.msg = msg
    def __str__(self):
        return self.msg

class CustomProcess:
    def __init__(self, queue, parameters):
        self.QUEUE = queue
        self.parameters = parameters

    def process(self):
        pass

class FileQueue(CustomProcess):
    def process(self):
        return [x for x in os.listdir() if os.path.isfile(x)]

class DirQueue(CustomProcess):
    def process(self):
        return [x for x in os.listdir() if os.path.isdir(x)]

class Filter(CustomProcess):
    def __init__(self, queue, parameters):
        super().__init__(queue, parameters)
        self.custom_filter = self.get_filter()
        
    def get_filter(self):
        repl = self.parameters[2] # to with separator will be replaced
        custom_filter = self.parameters[-1] if self.parameters[-1] != repl else ''
        return custom_filter

    def process(self):
        return list(filter(lambda x: self.custom_filter in x, self.QUEUE))

class SpFilterQueue(CustomProcess):
    def process(self):
        return list(map(lambda x: x.replace(' ', '_'), self.QUEUE))



class Renamer:
    QUEUE = []
    ROLLBACK_QUEUE = []
    MUST_HAVE_OPTIONS = [
        '-f', '-d'
    ]
    KEY_ALL = 'all'
    OPTIONS = {
        '-f': FileQueue,
        '-d': DirQueue,
        '-filter': Filter,
    }
    SIDE_OPTIONS = {
        '-sp': SpFilterQueue,
    }

    def __init__(self, args):
        self.args = args
        self.local_options = self.__preprocess_options(args)
        self.local_side_options = self.__preprocess_side_options(args)
        self.parameters = self.__preprocess_param(args, self.local_options)
        self.additional_check()

    def additional_check(self):
        """ Дополнительно проверяем особые случаи употребления аргументов и опций """
        if self.KEY_ALL not in self.parameters and \
            '-sp' in self.local_side_options:
            msg = "Cannot use the argument -sp without the flag 'all'"
            raise RenameError(msg)

    def __preprocess_options(self, all_args):
        """ Собирает все опции ([-f] например) в одну перменную
            дополнительно обрабатывает особые случаи употребления """
        options = [x for x in all_args if x in self.OPTIONS]
        if '-d' in options and '-f' in options:
            msg = "-d and -f are exclusive arguments you cannot use them in the same time "
            raise RenameError(msg)
        if not [x for x in options if x in self.MUST_HAVE_OPTIONS]:
            msg = "-d or -f are required arguments"
            raise RenameError(msg)
        return options

    def __preprocess_side_options(self, all_args):
        """ Собирает все  дополнительные опции ([-sp] например) в одну перменную
            они инициалицируются сразу после основных и МЕНЯЮТ названия файлов в основной очереди """
        return [x for x in all_args if x in self.SIDE_OPTIONS]

    def __preprocess_param(self, all_args, options):
        """ Сбор всех параметров, например имя файла, разделителя, заменителя
            жестко привязана к позиции параметров """
        other = [x for x in all_args if x not in options]
        if len(other) < 3 and not self.local_side_options:
            msg = "\nCannot do replace withouth any parameters. You need to point 3 parameters \n\
                    [PATH TO THE FILE/DIR or FILENAME/DIRNAME or 'all'] \n\
                    [SIMBOL TO REPLACE] \n\
                    [SIMBOL TO REPLACE WITH]"
            raise RenameError(msg)
        return other
        
    def __make_queue(self):
        """ Создаём очередь
            Сначала запускаем основные аргументы,
            затем создаём резервную копию имён
            запускаем вторичные аргументы, они могут менять основную очередь """

        for option in self.OPTIONS:
            if option in self.local_options:
                t = self.OPTIONS[option](self.QUEUE, self.parameters)
                self.QUEUE = t.process()

        self.ROLLBACK_QUEUE = self.QUEUE.copy()

        for option in self.SIDE_OPTIONS:
            if option in self.local_side_options:
                t = self.SIDE_OPTIONS[option](self.QUEUE, self.parameters)
                self.QUEUE = t.process()


    def do_rename(self, filename, delim, repl):
        """ Переименование файла, в зависимости от переденного 
            разделителя и заменителя """
        new_filename = filename.replace(delim, repl)
        os.rename(filename, new_filename)
        return new_filename

    def start_queue(self):
        """ Начало процесса переименования,
            если имеются вторичные аргументы, обрабатывается по особому,
            в основном случае при использовании "all" итерация по очереди 
            и переименование файлов,
            если изначально указан был один файл, то очередь состоит 
            из одного элемента """
        if self.local_side_options:
            for idx in range(len(self.QUEUE)):
                os.rename(self.ROLLBACK_QUEUE[idx], self.QUEUE[idx])
            return
        path, delim, repl, *_ = self.parameters
        if 'all' == path:
            for idx in range(len(self.QUEUE)):
                self.QUEUE[idx] = self.do_rename(self.QUEUE[idx], delim, repl)
        else:
            filename = os.path.split(os.path.abspath(path))[-1]
            new_filename = self.do_rename(filename, delim, repl)
            self.QUEUE = [new_filename]
            self.ROLLBACK_QUEUE = [filename]

    def rollback(self):
        """ откат имен фалов в исходное состояние """
        for idx in range(len(self.ROLLBACK_QUEUE)):
            os.rename(self.QUEUE[idx], self.ROLLBACK_QUEUE[idx])
            
    def save_or_not(self):
        answer = input('Save changes? [y/n]: ')
        if answer.lower() not in  ['y', 'yes', 'da', 'н', 'да']:
            self.rollback()

    def start(self):
        self.__make_queue()

        self.start_queue()

        self.save_or_not()


if __name__ == "__main__":
    r = Renamer(sys.argv[1:])
    r.start()

