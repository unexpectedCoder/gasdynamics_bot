import os
from enum import Enum
from sqlalchemy import BigInteger, Date, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import (
    AsyncAttrs, async_sessionmaker, create_async_engine
)


db_dir = "db_data"
if os.getenv("IN_DOCKER"):
    db_path = os.path.join("/", db_dir, "db.sqlite3")
else:
    db_path = os.path.join(db_dir, "db.sqlite3")

try:
    os.mkdir(os.path.realpath(os.path.join(db_path, os.path.pardir)))
except OSError:
    pass

engine = create_async_engine(url=f"sqlite+aiosqlite:///{db_path}")
async_session = async_sessionmaker(engine)


MAX_STR_LEN = 128


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    firstname: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    middlename: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    lastname: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    tg_id = mapped_column(BigInteger, nullable=True, unique=True)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    firstname: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    middlename: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    lastname: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    group: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    mark_book: Mapped[str] = mapped_column(String(MAX_STR_LEN), unique=True)
    tg_id = mapped_column(BigInteger, unique=True, nullable=True)

    def __str__(self):
        name = self.get_name()
        if self.tg_id:
            return f"{self.group} [{name}](tg://user?id={self.tg_id}) " \
                "(зачётка {self.mark_book})"
        return f"{self.group} {name} (зачётка {self.mark_book})"
    
    def get_name(self):
        return f"{self.lastname} {self.firstname} {self.middlename}"


class ControlWorksSem1(Base):
    __tablename__ = "control_works_sem_1"

    id: Mapped[int] = mapped_column(primary_key=True)
    approved_1: Mapped[bool] = mapped_column(default=False)
    points_1: Mapped[int] = mapped_column(default=0)
    approved_2: Mapped[bool] = mapped_column(default=False)
    points_2: Mapped[int] = mapped_column(default=0)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"), unique=True, nullable=True
    )


class ControlWorksSem2(Base):
    __tablename__ = "control_works_sem_2"

    id: Mapped[int] = mapped_column(primary_key=True)
    approved_1: Mapped[bool] = mapped_column(default=False)
    points_1: Mapped[int] = mapped_column(default=0)
    approved_2: Mapped[bool] = mapped_column(default=False)
    points_2: Mapped[int] = mapped_column(default=0)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"), unique=True, nullable=True
    )


class HomeworkNozzle(Base):
    __tablename__ = "homes_nozzle"

    id: Mapped[int] = mapped_column(primary_key=True)
    variant: Mapped[int] = mapped_column(unique=True)
    p0: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    T0: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    R: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    k: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    d_critic: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    area_ratio: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    d_chamber: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    alpha: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    beta: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    rel_propel_mass: Mapped[str] = mapped_column(String(MAX_STR_LEN))

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"), unique=True, nullable=True
    )
    deadline: Mapped[Date] = mapped_column(Date, nullable=True)
    approved: Mapped[bool] = mapped_column(default=False)
    approve_date: Mapped[Date] = mapped_column(Date, nullable=True)
    send: Mapped[bool] = mapped_column(default=False)
    done: Mapped[bool] = mapped_column(default=False)
    done_date: Mapped[Date] = mapped_column(Date, nullable=True)
    points: Mapped[int] = mapped_column(nullable=True)

    def __str__(self):
        head = f"Вариант ДЗ - {self.variant}:\n"

        p0 = "  - давление в камере " \
            f"_p_₀ = {round(float(self.p0)*1e-6, 2)} МПа;\n"
        T0 = f"  - температура в камере _T_₀ = {self.T0} К;\n"
        R = f"  - газовая постоянная _R_ = {self.R} Дж/(кг К);\n"
        k = f"  - показатель адиабаты _k_ = {self.k};\n"
        d_critic = \
            f"  - диаметр критического сечения _d_\* = {self.d_critic} м;\n"
        area_ratio = \
            f"  - отношение площадей выходного и критического сечений " \
            f"ν = {self.area_ratio};\n"
        d_chamber = \
            f"  - диаметр камеры сгорания _D_\_к = {self.d_chamber} м;\n"
        alpha = f"  - угол сужения конфузора α = {self.alpha}°;\n"
        beta = f"  - угол расширения диффузора β = {self.beta}°;\n"
        propel_mass = f"  - относительная масса топлива μ = {self.rel_propel_mass}."

        return head + p0 + T0 + R + k + d_critic + area_ratio + \
            d_chamber + alpha + beta + propel_mass


class HomeworkShockWedge(Base):
    __tablename__ = "homes_shock_wedge"

    id: Mapped[int] = mapped_column(primary_key=True)
    variant: Mapped[int] = mapped_column(unique=True)
    mach: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    beta1: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    beta2: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    beta3: Mapped[str] = mapped_column(String(MAX_STR_LEN))

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"), unique=True, nullable=True
    )
    deadline: Mapped[Date] = mapped_column(Date, nullable=True)
    approved: Mapped[bool] = mapped_column(default=False)
    approve_date: Mapped[Date] = mapped_column(Date, nullable=True)
    send: Mapped[bool] = mapped_column(default=False)
    done: Mapped[bool] = mapped_column(default=False)
    done_date: Mapped[Date] = mapped_column(Date, nullable=True)
    points: Mapped[int] = mapped_column(nullable=True)

    def __str__(self):
        text = f"Вариант ДЗ *№{self.variant}*:\n\n"

        mach = f"  - скорость набегающего потока M = {self.mach};\n"
        beta1 = f"  - угол β₁ = {self.beta1}°;\n"
        beta2 = f"  - угол β₂ = {self.beta2}°;\n"
        beta3 = f"  - угол β₃ = {self.beta3}°;\n"
        k = "  - показатель адиабаты воздуха _k_ = 1.4."

        return text + mach + beta1 + beta2 + beta3 + k


class Lab_1(Base):
    __tablename__ = "lab_1"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"), unique=True, nullable=True
    )
    send: Mapped[bool] = mapped_column(default=False)
    done: Mapped[bool] = mapped_column(default=False)
    done_date: Mapped[Date] = mapped_column(Date, nullable=True)
    points: Mapped[int] = mapped_column(nullable=True)


class Lab_2(Base):
    __tablename__ = "lab_2"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"), unique=True, nullable=True
    )
    send: Mapped[bool] = mapped_column(default=False)
    done: Mapped[bool] = mapped_column(default=False)
    done_date: Mapped[Date] = mapped_column(Date, nullable=True)
    points: Mapped[int] = mapped_column(nullable=True)


class Lab_3(Base):
    __tablename__ = "lab_3"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"), unique=True, nullable=True
    )
    send: Mapped[bool] = mapped_column(default=False)
    done: Mapped[bool] = mapped_column(default=False)
    done_date: Mapped[Date] = mapped_column(Date, nullable=True)
    points: Mapped[int] = mapped_column(nullable=True)


class Lab_4(Base):
    __tablename__ = "lab_4"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"), unique=True, nullable=True
    )
    send: Mapped[bool] = mapped_column(default=False)
    done: Mapped[bool] = mapped_column(default=False)
    done_date: Mapped[Date] = mapped_column(Date, nullable=True)
    points: Mapped[int] = mapped_column(nullable=True)


class Lab_5(Base):
    __tablename__ = "lab_5"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"), unique=True, nullable=True
    )
    send: Mapped[bool] = mapped_column(default=False)
    done: Mapped[bool] = mapped_column(default=False)
    done_date: Mapped[Date] = mapped_column(Date, nullable=True)
    points: Mapped[int] = mapped_column(nullable=True)


class Lab_6(Base):
    __tablename__ = "lab_6"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"), unique=True, nullable=True
    )
    send: Mapped[bool] = mapped_column(default=False)
    done: Mapped[bool] = mapped_column(default=False)
    done_date: Mapped[Date] = mapped_column(Date, nullable=True)
    points: Mapped[int] = mapped_column(nullable=True)


class Labs(Enum):
    LAB_1 = 1
    LAB_2 = 2
    LAB_3 = 3
    LAB_4 = 4
    LAB_5 = 5
    LAB_6 = 6


LABS_TYPES = {
    Labs.LAB_1.value: Lab_1,
    Labs.LAB_2.value: Lab_2,
    Labs.LAB_3.value: Lab_3,
    Labs.LAB_4.value: Lab_4,
    Labs.LAB_5.value: Lab_5,
    Labs.LAB_6.value: Lab_6
}


AnyLab = Lab_1 | Lab_2 | Lab_3 | Lab_4 | Lab_5 | Lab_6
AnyHomework = HomeworkNozzle | HomeworkShockWedge


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
