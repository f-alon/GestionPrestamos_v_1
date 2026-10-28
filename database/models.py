from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from database.connection import Base
from config import DATETIME_FORMAT

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    telefono = Column(String, nullable=False)  # Formato internacional sin simbolos, ej: 54911xxxxxxxx
    email = Column(String, nullable=True)
    notas = Column(Text, nullable=True)
    fecha_alta = Column(String, nullable=False, default=lambda: datetime.now().strftime(DATETIME_FORMAT))

    prestamos = relationship("Prestamo", back_populates="cliente", cascade="all, delete-orphan", order_by="desc(Prestamo.id)")

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()

    def __repr__(self):
        return f"<Cliente(id={self.id}, nombre='{self.nombre_completo}', telefono='{self.telefono}')>"


class Prestamo(Base):
    __tablename__ = "prestamos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    monto_prestado = Column(Float, nullable=False)
    porcentaje_interes = Column(Float, nullable=False)
    tipo_plazo = Column(String, nullable=False)  # 'DIAS' o 'SEMANAS'
    duracion_plazo = Column(Integer, nullable=False)
    fecha_inicio = Column(String, nullable=False)  # 'YYYY-MM-DD'
    fecha_fin = Column(String, nullable=False)     # 'YYYY-MM-DD'
    tasa_mora_diaria = Column(Float, nullable=False)
    estado = Column(String, nullable=False, default="EN_CURSO")  # 'EN_CURSO' o 'TERMINADO'

    cliente = relationship("Cliente", back_populates="prestamos")
    pagos = relationship("Pago", back_populates="prestamo", cascade="all, delete-orphan", order_by="Pago.fecha_pago")

    def __repr__(self):
        return f"<Prestamo(id={self.id}, cliente_id={self.cliente_id}, monto={self.monto_prestado}, estado='{self.estado}')>"


class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id", ondelete="CASCADE"), nullable=False)
    monto = Column(Float, nullable=False)
    fecha_pago = Column(String, nullable=False, default=lambda: datetime.now().strftime(DATETIME_FORMAT))
    metodo_pago = Column(String, nullable=True, default="Efectivo")  # Efectivo, Transferencia, etc.
    comprobante_ref = Column(String, nullable=True)

    prestamo = relationship("Prestamo", back_populates="pagos")

    def __repr__(self):
        return f"<Pago(id={self.id}, prestamo_id={self.prestamo_id}, monto={self.monto}, fecha='{self.fecha_pago}')>"

