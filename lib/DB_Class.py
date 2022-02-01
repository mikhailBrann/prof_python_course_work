from datetime import datetime
from random import randrange
import sqlalchemy as sq
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
# импорт конфигов для подключения к БД и сервисам VK
from lib.db_config import db_name, db_user, db_password, vk_token, vk_user, vk_pass


Base = declarative_base()
class User(Base):
    """ класс-шаблон пользователя для БД """

    __tablename__ = 'users'
    id = sq.Column(sq.Integer, primary_key=True)
    user_vk_id = sq.Column(sq.Integer, nullable=False)
    user_first_name = sq.Column(sq.String, nullable=False)
    user_last_name = sq.Column(sq.String, nullable=False)
    parent_id = sq.Column(sq.Integer, nullable=False)


class DB:
    """ класс для работы с БД """

    def __init__(self, user=db_user, password=db_password, datebase=db_name):
        """ метод инициализирует подключение к БД"""
        dns = f"postgresql://{user}:{password}@localhost:5432/{datebase}"
        self.db_engine = sq.create_engine(dns)
        sessionInit = sessionmaker(bind=self.db_engine)
        self.session = sessionInit()

    def verificationOnBase(self, vk_id):
        """
        метод проверяет существование таблицы с пользователями,
        а так-же проверяет наличие пользователя в таблице по полю 'user_vk_id'
        """

        # обработчик для таблиц
        Base.metadata.create_all(self.db_engine)

        # проверяем, есть ли такой пользователь в БД
        check_user_to_db = self.session.query(User).filter(User.user_vk_id == vk_id).all()
        if not check_user_to_db:
            return True
        else:
            return False

    def createUser(self, vk_id, user_first_name, user_last_name, parent_id):
        """ метод создает пользователя в БД """

        new_user = User(
            user_vk_id=vk_id,
            user_first_name=user_first_name,
            user_last_name=user_last_name,
            parent_id=parent_id
        )

        # добавляем запись в сессию и комитим
        self.session.add(new_user)
        self.session.commit()


class VK:
    """ класс для работы с ВК API """

    def __init__(self):
        self.session = vk_api.VkApi(token=vk_token)
        self.longpoll = VkLongPoll(self.session)
        self.api = self.session.get_api()

        self.user_vk_session = vk_api.VkApi(vk_user, vk_pass)
        self.user_vk_session.auth()
        self.user_vk_api = self.user_vk_session.get_api()

    def findVkUsers(self, user_date):
        """
            метод для поиска пары пользователю,
            входные данные - dict со свойствами пользователя
        """

        data_base = DB()
        result_list = []
        count_val = 1
        offset_val = count_val + 1
        end_while = 0

        # проверяем, указан ли год рождения и получаем возраст для поиска
        current_year = datetime.now()
        seeking_user_years = int(current_year.year) - int(user_date["bdate"][-4:]) if len(user_date["bdate"]) > 6 else False

        # определяем пол(если мужской или неопределился то задаем женский для пары)
        set_sex = 1
        if user_date["sex"] == 1 or user_date["sex"] == 0:
            set_sex = 2

        while True:
            serch_users_result = self.user_vk_api.users.search(
                sort=1,
                city=user_date['city']['id'],
                count=count_val,
                offset=offset_val,
                sex=set_sex,
                status=user_date['relation'],
                age_from=18,
                age_to=seeking_user_years,
                fields=['bdate', 'sex', 'city', 'relation']
            )

            result_list += serch_users_result['items']

            for found_user in result_list:
                if data_base.verificationOnBase(found_user['id']):
                    # записываем пользователя в БД
                    data_base.createUser(
                        vk_id=found_user['id'],
                        user_first_name=found_user['first_name'],
                        user_last_name=found_user['last_name'],
                        parent_id=user_date['id']
                    )

                    return found_user

            offset_val += 1
            end_while += 1
            # ограничиваем выборку на 1500 результатах
            if end_while > 1500:
                break

    def listener(self):
        """
        метод при помощи API 'прослушивает' активность в группе в ВК.
        Если пользователь напишет в группу или в беседу группы,
        бот ВК будет обрататывать его ввод
        """

        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:

                # запрашиваем поля пользователя из диалога
                seeking_user = self.api.users.get(user_ids=event.user_id, fields=['bdate', 'sex', 'city', 'relation'], name_case='nom')
                seeking_user = seeking_user[0]

                # Если написали в ЛС
                if event.from_user:

                    if event.text.lower() == 'найди друга':
                        self.api.messages.send(
                            user_id=event.user_id,
                            message=f"Ура, начинаем искать!",
                            random_id=randrange(10 ** 7)
                        )

                        finded_result = self.findVkUsers(seeking_user)

                        self.api.messages.send(
                            user_id=event.user_id,
                            message=f'Твой друг - [id{finded_result["id"]}|{finded_result["first_name"]} {finded_result["last_name"]}]',
                            random_id=randrange(10 ** 7)
                        )

                    else:
                        self.api.messages.send(
                            user_id=event.user_id,
                            message=f"{seeking_user['first_name']} - подобрать тебе друга (просто напиши 'найди друга')?",
                            random_id=randrange(10 ** 7)
                        )


                # Если написали в Беседе
                elif event.from_chat:

                    if event.text.lower() == 'найди друга':
                        self.api.messages.send(
                            chat_id=event.chat_id,
                            message=f"Ура, начинаем искать!",
                            random_id=randrange(10 ** 7)
                        )

                        finded_result = self.findVkUsers(seeking_user)

                        self.api.messages.send(
                            chat_id=event.chat_id,
                            message=f'{seeking_user["first_name"]}, твой друг - [id{finded_result["id"]}|{finded_result["first_name"]} {finded_result["last_name"]}]',
                            random_id=randrange(10 ** 7)
                        )

                    else:
                        self.api.messages.send(
                            chat_id=event.chat_id,
                            message=f"{seeking_user['first_name']} - подобрать тебе друга (просто напиши 'найди друга')?",
                            random_id=randrange(10 ** 7)
                        )

VK_USER = VK()


