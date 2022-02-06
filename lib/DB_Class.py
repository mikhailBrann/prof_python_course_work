import sqlalchemy as sq
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# импорт конфигов для подключения к БД
from lib.db_config import db_name, db_user, db_password

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
