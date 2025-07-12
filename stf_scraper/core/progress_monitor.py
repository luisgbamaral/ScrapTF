"""
Módulo para monitoramento de progresso do scraping.
Fornece funcionalidades para acompanhar o progresso em tempo real.
"""

import time
import threading
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..utils.logger import get_logger


@dataclass
class ProgressStats:
    """Estatísticas de progresso."""
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    start_time: Optional[datetime] = None
    current_item: str = ""

    @property
    def completion_percentage(self) -> float:
        """Calcula percentual de conclusão."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100

    @property
    def success_rate(self) -> float:
        """Calcula taxa de sucesso."""
        if self.processed_items == 0:
            return 0.0
        return (self.successful_items / self.processed_items) * 100

    @property
    def elapsed_time(self) -> timedelta:
        """Tempo decorrido desde o início."""
        if self.start_time is None:
            return timedelta(0)
        return datetime.now() - self.start_time

    @property
    def estimated_remaining_time(self) -> timedelta:
        """Estima tempo restante."""
        if self.processed_items == 0 or self.start_time is None:
            return timedelta(0)

        elapsed = self.elapsed_time
        rate = self.processed_items / elapsed.total_seconds()
        remaining_items = self.total_items - self.processed_items

        if rate > 0:
            remaining_seconds = remaining_items / rate
            return timedelta(seconds=remaining_seconds)

        return timedelta(0)

    @property
    def items_per_second(self) -> float:
        """Calcula itens processados por segundo."""
        if self.start_time is None:
            return 0.0

        elapsed = self.elapsed_time.total_seconds()
        if elapsed > 0:
            return self.processed_items / elapsed
        return 0.0


class ProgressMonitor:
    """
    Monitor de progresso para operações de scraping.

    Fornece funcionalidades para:
    - Acompanhar progresso em tempo real
    - Calcular estatísticas de performance
    - Notificar callbacks sobre mudanças
    - Exibir progresso no console
    """

    def __init__(
        self,
        total_items: int = 0,
        update_interval: float = 1.0,
        enable_console_output: bool = True,
        console_update_interval: float = 2.0
    ):
        """
        Inicializa o monitor de progresso.

        Args:
            total_items: Número total de itens a processar
            update_interval: Intervalo de atualização em segundos
            enable_console_output: Se deve exibir progresso no console
            console_update_interval: Intervalo de atualização do console
        """
        self.stats = ProgressStats(total_items=total_items)
        self.update_interval = update_interval
        self.enable_console_output = enable_console_output
        self.console_update_interval = console_update_interval

        self._callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._console_thread: Optional[threading.Thread] = None
        self._stop_console = threading.Event()
        self._logger = get_logger(__name__)

        # Histórico para cálculos de velocidade
        self._history: list = []
        self._max_history_size = 100

    def start(self) -> None:
        """Inicia o monitoramento."""
        with self._lock:
            self.stats.start_time = datetime.now()
            self._stop_console.clear()

            if self.enable_console_output:
                self._start_console_output()

        self._logger.info(f"Monitoramento iniciado para {self.stats.total_items} itens")

    def stop(self) -> None:
        """Para o monitoramento."""
        with self._lock:
            self._stop_console.set()

            if self._console_thread and self._console_thread.is_alive():
                self._console_thread.join(timeout=1.0)

        self._logger.info("Monitoramento finalizado")

    def update_progress(
        self,
        processed: Optional[int] = None,
        successful: Optional[int] = None,
        failed: Optional[int] = None,
        current_item: Optional[str] = None
    ) -> None:
        """
        Atualiza o progresso.

        Args:
            processed: Número de itens processados
            successful: Número de itens bem-sucedidos
            failed: Número de itens que falharam
            current_item: Item atual sendo processado
        """
        with self._lock:
            if processed is not None:
                self.stats.processed_items = processed

            if successful is not None:
                self.stats.successful_items = successful

            if failed is not None:
                self.stats.failed_items = failed

            if current_item is not None:
                self.stats.current_item = current_item

            # Adiciona ao histórico
            self._add_to_history()

            # Notifica callbacks
            self._notify_callbacks()

    def increment_progress(
        self,
        processed: int = 1,
        successful: int = 0,
        failed: int = 0,
        current_item: Optional[str] = None
    ) -> None:
        """
        Incrementa o progresso.

        Args:
            processed: Incremento de itens processados
            successful: Incremento de itens bem-sucedidos
            failed: Incremento de itens que falharam
            current_item: Item atual sendo processado
        """
        with self._lock:
            self.stats.processed_items += processed
            self.stats.successful_items += successful
            self.stats.failed_items += failed

            if current_item is not None:
                self.stats.current_item = current_item

            # Adiciona ao histórico
            self._add_to_history()

            # Notifica callbacks
            self._notify_callbacks()

    def set_total_items(self, total: int) -> None:
        """Define o número total de itens."""
        with self._lock:
            self.stats.total_items = total

    def add_callback(self, name: str, callback: Callable[[ProgressStats], None]) -> None:
        """
        Adiciona callback para notificações de progresso.

        Args:
            name: Nome do callback
            callback: Função a ser chamada com as estatísticas
        """
        self._callbacks[name] = callback

    def remove_callback(self, name: str) -> None:
        """Remove callback."""
        self._callbacks.pop(name, None)

    def get_stats(self) -> ProgressStats:
        """Retorna cópia das estatísticas atuais."""
        with self._lock:
            return ProgressStats(
                total_items=self.stats.total_items,
                processed_items=self.stats.processed_items,
                successful_items=self.stats.successful_items,
                failed_items=self.stats.failed_items,
                start_time=self.stats.start_time,
                current_item=self.stats.current_item
            )

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas detalhadas."""
        stats = self.get_stats()

        return {
            'total_items': stats.total_items,
            'processed_items': stats.processed_items,
            'successful_items': stats.successful_items,
            'failed_items': stats.failed_items,
            'completion_percentage': stats.completion_percentage,
            'success_rate': stats.success_rate,
            'elapsed_time_seconds': stats.elapsed_time.total_seconds(),
            'estimated_remaining_seconds': stats.estimated_remaining_time.total_seconds(),
            'items_per_second': stats.items_per_second,
            'current_item': stats.current_item,
            'start_time': stats.start_time.isoformat() if stats.start_time else None
        }

    def _add_to_history(self) -> None:
        """Adiciona ponto ao histórico."""
        now = datetime.now()
        self._history.append({
            'timestamp': now,
            'processed': self.stats.processed_items,
            'successful': self.stats.successful_items,
            'failed': self.stats.failed_items
        })

        # Limita tamanho do histórico
        if len(self._history) > self._max_history_size:
            self._history.pop(0)

    def _notify_callbacks(self) -> None:
        """Notifica todos os callbacks registrados."""
        stats = self.get_stats()

        for name, callback in self._callbacks.items():
            try:
                callback(stats)
            except Exception as e:
                self._logger.error(f"Erro no callback '{name}': {e}")

    def _start_console_output(self) -> None:
        """Inicia thread para saída no console."""
        self._console_thread = threading.Thread(
            target=self._console_output_loop,
            daemon=True
        )
        self._console_thread.start()

    def _console_output_loop(self) -> None:
        """Loop principal para saída no console."""
        while not self._stop_console.wait(self.console_update_interval):
            self._print_progress()

    def _print_progress(self) -> None:
        """Imprime progresso no console."""
        stats = self.get_stats()

        # Barra de progresso
        bar_length = 40
        filled_length = int(bar_length * stats.completion_percentage / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)

        # Informações de tempo
        elapsed_str = str(stats.elapsed_time).split('.')[0]  # Remove microssegundos
        remaining_str = str(stats.estimated_remaining_time).split('.')[0]

        # Linha de progresso
        progress_line = (
            f"\r[{bar}] {stats.completion_percentage:6.2f}% "
            f"({stats.processed_items}/{stats.total_items}) "
            f"| ✓{stats.successful_items} ✗{stats.failed_items} "
            f"| {stats.items_per_second:.1f} it/s "
            f"| {elapsed_str}<{remaining_str}"
        )

        print(progress_line, end='', flush=True)

        # Item atual (em nova linha se muito longo)
        if stats.current_item and len(stats.current_item) > 50:
            print(f"\nProcessando: {stats.current_item[:50]}...")

    def print_final_summary(self) -> None:
        """Imprime resumo final."""
        stats = self.get_stats()

        print("\n" + "="*60)
        print("📊 RESUMO FINAL DO PROGRESSO")
        print("="*60)
        print(f"✅ Total processado: {stats.processed_items}/{stats.total_items}")
        print(f"🎯 Taxa de sucesso: {stats.success_rate:.1f}%")
        print(f"⏱️  Tempo total: {stats.elapsed_time}")
        print(f"🚀 Velocidade média: {stats.items_per_second:.2f} itens/segundo")

        if stats.failed_items > 0:
            print(f"⚠️  Itens com falha: {stats.failed_items}")

        print("="*60)


def create_progress_monitor(
    total_items: int,
    enable_console: bool = True,
    callbacks: Optional[Dict[str, Callable]] = None
) -> ProgressMonitor:
    """
    Factory function para criar monitor de progresso.

    Args:
        total_items: Número total de itens
        enable_console: Se deve exibir no console
        callbacks: Callbacks opcionais

    Returns:
        Instância configurada do ProgressMonitor
    """
    monitor = ProgressMonitor(
        total_items=total_items,
        enable_console_output=enable_console
    )

    if callbacks:
        for name, callback in callbacks.items():
            monitor.add_callback(name, callback)

    return monitor
