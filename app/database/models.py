import os
from datetime import date
from enum import Enum

from sqlalchemy import BigInteger, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
    relationship,
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


class HomeworkMixin:
    id: Mapped[int] = mapped_column(primary_key=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    approved: Mapped[bool] = mapped_column(default=False)
    approve_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    send: Mapped[bool] = mapped_column(default=False)
    done: Mapped[bool] = mapped_column(default=False)
    done_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    points: Mapped[int | None] = mapped_column(nullable=True)

    @declared_attr
    def student_id(cls) -> Mapped[int | None]:
        return mapped_column(ForeignKey("students.id"), unique=True, nullable=True)


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    firstname: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    middlename: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    lastname: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    tg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    firstname: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    middlename: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    lastname: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    group: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    mark_book: Mapped[str] = mapped_column(String(MAX_STR_LEN), unique=True)
    tg_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)

    labs: Mapped[list["Lab"]] = relationship(back_populates="student", lazy="raise")
    control_works: Mapped[list["ControlWork"]] = relationship(
        back_populates="student", lazy="raise"
    )
    homework_nozzle: Mapped["HomeworkNozzle | None"] = relationship(
        back_populates="student", lazy="raise"
    )
    homework_shock_wedge: Mapped["HomeworkShockWedge | None"] = relationship(
        back_populates="student", lazy="raise"
    )

    def __str__(self):
        name = self.get_name()
        if self.tg_id:
            return (
                f"{self.group} [{name}](tg://user?id={self.tg_id}) "
                f"(зачётка {self.mark_book})"
            )
        return f"{self.group} {name} (зачётка {self.mark_book})"

    def get_name(self):
        return f"{self.lastname} {self.firstname} {self.middlename}"


class ControlWork(Base):
    __tablename__ = "control_works"

    id: Mapped[int] = mapped_column(primary_key=True)
    control_number: Mapped[int] = mapped_column()
    approved: Mapped[bool] = mapped_column(default=False)
    points: Mapped[int] = mapped_column(default=0)
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id"), nullable=True
    )

    student: Mapped["Student | None"] = relationship(
        back_populates="control_works", lazy="raise"
    )

    __table_args__ = (UniqueConstraint("student_id", "control_number"),)


class HomeworkNozzle(HomeworkMixin, Base):
    __tablename__ = "homes_nozzle"

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

    student: Mapped["Student | None"] = relationship(
        back_populates="homework_nozzle", lazy="raise"
    )

    def __str__(self):
        head = f"Вариант ДЗ - {self.variant}:\n"

        p0 = f"  - давление в камере {round(float(self.p0) * 1e-6, 2)} МПа;\n"
        T0 = f"  - температура в камере {self.T0} К;\n"
        R = f"  - газовая постоянная {self.R} Дж/(кг К);\n"
        k = f"  - показатель адиабаты {self.k};\n"
        d_critic = f"  - диаметр критического сечения {self.d_critic} м;\n"
        area_ratio = f"  - отношение площадей выходного и критического сечений {self.area_ratio};\n"
        d_chamber = f"  - диаметр камеры сгорания {self.d_chamber} м;\n"
        alpha = f"  - угол сужения конфузора {self.alpha}°;\n"
        beta = f"  - угол расширения диффузора {self.beta}°;\n"
        propel_mass = f"  - относительная масса топлива {self.rel_propel_mass}."

        return (
            head
            + p0
            + T0
            + R
            + k
            + d_critic
            + area_ratio
            + d_chamber
            + alpha
            + beta
            + propel_mass
        )


class HomeworkShockWedge(HomeworkMixin, Base):
    __tablename__ = "homes_shock_wedge"

    variant: Mapped[int] = mapped_column(unique=True)
    mach: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    beta1: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    beta2: Mapped[str] = mapped_column(String(MAX_STR_LEN))
    beta3: Mapped[str] = mapped_column(String(MAX_STR_LEN))

    student: Mapped["Student | None"] = relationship(
        back_populates="homework_shock_wedge", lazy="raise"
    )

    def __str__(self):
        text = f"Вариант ДЗ №{self.variant}:\n\n"

        mach = f"  - скорость набегающего потока M = {self.mach};\n"
        beta1 = f"  - угол β₁ = {self.beta1}°;\n"
        beta2 = f"  - угол β₂ = {self.beta2}°;\n"
        beta3 = f"  - угол β₃ = {self.beta3}°;\n"
        k = "  - показатель адиабаты воздуха 1.4."

        return text + mach + beta1 + beta2 + beta3 + k


class Lab(Base):
    __tablename__ = "labs"

    id: Mapped[int] = mapped_column(primary_key=True)
    lab_number: Mapped[int] = mapped_column()
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id"), nullable=True
    )
    send: Mapped[bool] = mapped_column(default=False)
    done: Mapped[bool] = mapped_column(default=False)
    done_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    points: Mapped[int | None] = mapped_column(nullable=True)

    student: Mapped["Student | None"] = relationship(
        back_populates="labs", lazy="raise"
    )

    __table_args__ = (UniqueConstraint("student_id", "lab_number"),)


class LabNumber(Enum):
    LAB_1 = 1
    LAB_2 = 2
    LAB_3 = 3
    LAB_4 = 4
    LAB_5 = 5
    LAB_6 = 6


class ControlNumber(Enum):
    CONTROL_SEM1_1 = 1
    CONTROL_SEM1_2 = 2
    CONTROL_SEM2_1 = 3
    CONTROL_SEM2_2 = 4


AnyHomework = HomeworkNozzle | HomeworkShockWedge


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
